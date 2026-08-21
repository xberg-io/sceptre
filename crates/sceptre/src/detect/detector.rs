//! Internal text-detection seam, its stage DTOs, and the CRAFT runner.
//!
//! The detector consumes a decoded [`Image`] and yields raw corner regions. The
//! stage boundary deliberately uses plain `[x, y]` corner arrays rather than the
//! public [`Quad`](crate::types::Quad), keeping the detector decoupled from the
//! result surface until the engine maps regions back to public types.
//!
//! [`CraftDetector`] wires the four detection stages together: preprocess →
//! CRAFT forward pass → postprocess → group.

use std::sync::Arc;

use crate::config::DetectionConfig;
use crate::error::Result;
use crate::inference::ModelBackend;
use crate::types::{Image, QUAD_CORNERS as REGION_CORNERS};

use super::group::Grouped;

/// Internal seam: turns a decoded image into candidate text regions.
pub(crate) trait TextDetector: Send + Sync {
    /// Detect text regions in `input`.
    fn detect(&self, input: &DetectorInput) -> Result<DetectedRegions>;
}

/// Internal DTO: what the detector consumes. Borrows the decoded image.
pub(crate) struct DetectorInput<'a> {
    /// The decoded image to detect text in.
    pub image: &'a Image,
}

/// Internal DTO: the detected regions produced by a [`TextDetector`].
pub(crate) struct DetectedRegions {
    /// One entry per detected region.
    pub regions: Vec<DetectedRegion>,
}

/// Internal DTO: a single detected region as raw corners.
pub(crate) struct DetectedRegion {
    /// Corner coordinates `[x, y]`, clockwise from top-left.
    pub corners: [[f32; 2]; REGION_CORNERS],
    /// Whether this region is an axis-aligned box (`true`) or a free/rotated quad
    /// (`false`). The crop stage uses this to pick an axis-aligned crop versus a
    /// perspective warp.
    pub axis_aligned: bool,
}

/// The CRAFT-based text detector.
pub(crate) struct CraftDetector {
    backend: Arc<dyn ModelBackend>,
    config: DetectionConfig,
    /// Fixed square canvas for the CRAFT input, or `None` for the dynamic-shape path.
    /// Set to `Some(canvas)` on the `tract` backend, whose loaded model is pinned to
    /// the matching `[1, 3, canvas, canvas]` shape (see ADR 0027).
    fixed_canvas: Option<u32>,
}

impl CraftDetector {
    /// Construct a CRAFT detector from a loaded model backend and detection config.
    ///
    /// `fixed_canvas` pins the detection input to a fixed square canvas (tract); pass
    /// `None` for the dynamic-shape path (ort).
    pub(crate) fn new(
        backend: Arc<dyn ModelBackend>,
        detection_config: DetectionConfig,
        fixed_canvas: Option<u32>,
    ) -> Self {
        Self {
            backend,
            config: detection_config,
            fixed_canvas,
        }
    }
}

impl TextDetector for CraftDetector {
    /// Run the full CRAFT pipeline: resize/normalize, forward pass to
    /// heat-maps, threshold into boxes, scale back to image space, and group
    /// into lines. `input.image` is detected exactly as given — any whole-page
    /// orientation decision is the caller's job (see `engine::sceptre_engine`
    /// and the `orientation` module), so both detection and recognition agree
    /// on which frame they are running in.
    fn detect(&self, input: &DetectorInput) -> Result<DetectedRegions> {
        let prepared = super::preprocess::prepare_with_canvas(
            input.image,
            self.config.canvas_size,
            self.config.mag_ratio,
            self.fixed_canvas,
            self.config.max_megapixels,
        )?;
        let heat = super::craft::run_craft(self.backend.as_ref(), prepared.tensor)?;
        let mut boxes = super::postprocess::get_det_boxes(
            &heat.region,
            &heat.link,
            self.config.text_threshold,
            self.config.link_threshold,
            self.config.low_text,
        )?;
        super::postprocess::adjust_coordinates(&mut boxes, prepared.inv_ratio);
        let grouped = super::group::group_boxes(&boxes, &self.config);
        let regions = map_grouped_to_regions(grouped, self.config.min_size);
        Ok(DetectedRegions { regions })
    }
}

/// Map grouped boxes to [`DetectedRegion`]s, converting horizontal boxes to
/// clockwise corners, dropping regions no larger than `min_size`, and restoring
/// top-to-bottom reading order across the horizontal/free split (see
/// [`sort_regions_into_reading_order`]).
///
/// A region is kept only when `max(width, height) > min_size` (strict, matching
/// EasyOCR's small-box filter); `width` and `height` are the corner-extent spans.
fn map_grouped_to_regions(grouped: Grouped, min_size: u32) -> Vec<DetectedRegion> {
    let min_size = min_size as f32;
    let mut regions = Vec::with_capacity(grouped.horizontal.len() + grouped.free.len());
    for [x_min, x_max, y_min, y_max] in grouped.horizontal {
        let corners = [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]];
        push_if_large_enough(&mut regions, corners, true, min_size);
    }
    for corners in grouped.free {
        push_if_large_enough(&mut regions, corners, false, min_size);
    }
    sort_regions_into_reading_order(&mut regions);
    regions
}

/// Stable-sort `regions` into top-to-bottom, left-to-right reading order.
///
/// [`group::group_boxes`] returns horizontal (line-grouped) boxes and free
/// (rotated) quads as two *separate* lists, split purely by slope classification,
/// not by page position. [`map_grouped_to_regions`] previously concatenated
/// horizontal-then-free unconditionally, so a region merely *misclassified* as
/// free — a borderline slope call on a short or punctuation-adjacent word, which
/// costs only 1-2px of corner noise (see
/// `group::should_route_near_identical_quads_to_opposite_paths_at_the_slope_boundary`)
/// — was silently relocated from wherever it sat on the page to the very end of
/// the whole region list, downstream of every other line on the page. A stable
/// sort by vertical center restores true reading order regardless of which
/// classification bucket a region landed in. Regions whose centers fall within
/// half the shorter region's height are treated as one text row and sorted by
/// their left edge. This keeps mixed-size glyphs on the same row without letting
/// a tall central label absorb an adjacent row.
fn sort_regions_into_reading_order(regions: &mut [DetectedRegion]) {
    regions.sort_by(|a, b| region_geometry(&a.corners).0.total_cmp(&region_geometry(&b.corners).0));

    let mut row_start = 0;
    while row_start < regions.len() {
        let (first_center, first_height, _) = region_geometry(&regions[row_start].corners);
        let mut center_sum = first_center;
        let mut row_len = 1;
        let mut min_height = first_height;
        let mut row_end = row_start + 1;

        while row_end < regions.len() {
            let (center, height, _) = region_geometry(&regions[row_end].corners);
            let row_center = center_sum / row_len as f32;
            if center - row_center > 0.5 * min_height.min(height) {
                break;
            }
            center_sum += center;
            row_len += 1;
            min_height = min_height.min(height);
            row_end += 1;
        }

        regions[row_start..row_end]
            .sort_by(|a, b| region_geometry(&a.corners).2.total_cmp(&region_geometry(&b.corners).2));
        row_start = row_end;
    }
}

/// `(vertical center, height, left edge)` of a region's corners.
fn region_geometry(corners: &[[f32; 2]; REGION_CORNERS]) -> (f32, f32, f32) {
    let mut min_x = f32::MAX;
    let mut min_y = f32::MAX;
    let mut max_y = f32::MIN;
    for corner in corners {
        min_x = min_x.min(corner[0]);
        min_y = min_y.min(corner[1]);
        max_y = max_y.max(corner[1]);
    }
    (0.5 * (min_y + max_y), max_y - min_y, min_x)
}

/// Push a region only if its larger extent strictly exceeds `min_size`, else drop it.
fn push_if_large_enough(
    regions: &mut Vec<DetectedRegion>,
    corners: [[f32; 2]; REGION_CORNERS],
    axis_aligned: bool,
    min_size: f32,
) {
    if region_max_extent(&corners) > min_size {
        regions.push(DetectedRegion { corners, axis_aligned });
    }
}

/// Larger of the corner-extent width and height of a region.
fn region_max_extent(corners: &[[f32; 2]; REGION_CORNERS]) -> f32 {
    let mut min_x = f32::MAX;
    let mut max_x = f32::MIN;
    let mut min_y = f32::MAX;
    let mut max_y = f32::MIN;
    for corner in corners {
        min_x = min_x.min(corner[0]);
        max_x = max_x.max(corner[0]);
        min_y = min_y.min(corner[1]);
        max_y = max_y.max(corner[1]);
    }
    (max_x - min_x).max(max_y - min_y)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::inference::Tensor;
    use ndarray::{ArrayD, IxDyn};

    /// A backend returning a fixed CRAFT heat-map, so [`CraftDetector::detect`] can
    /// be exercised end-to-end without a real ONNX model.
    struct FixedBackend {
        output: ArrayD<f32>,
    }

    impl ModelBackend for FixedBackend {
        fn name(&self) -> &str {
            "fixed"
        }

        fn run(&self, _input: Tensor) -> Result<Tensor> {
            Ok(self.output.clone())
        }
    }

    fn solid_image(width: u32, height: u32) -> Image {
        let pixels = vec![255u8; (width * height * 3) as usize];
        Image::from_rgb8(width, height, pixels).expect("valid rgb buffer")
    }

    #[test]
    fn should_map_horizontal_box_to_axis_aligned_corners() {
        let grouped = Grouped {
            horizontal: vec![[10.0, 50.0, 20.0, 60.0]],
            free: Vec::new(),
        };

        let regions = map_grouped_to_regions(grouped, 0);

        assert_eq!(regions.len(), 1);
        assert!(regions[0].axis_aligned);
        assert_eq!(
            regions[0].corners,
            [[10.0, 20.0], [50.0, 20.0], [50.0, 60.0], [10.0, 60.0]]
        );
    }

    #[test]
    fn should_map_free_quad_to_non_axis_aligned_region() {
        let quad = [[10.0, 12.0], [50.0, 20.0], [48.0, 60.0], [8.0, 52.0]];
        let grouped = Grouped {
            horizontal: Vec::new(),
            free: vec![quad],
        };

        let regions = map_grouped_to_regions(grouped, 0);

        assert_eq!(regions.len(), 1);
        assert!(!regions[0].axis_aligned);
        assert_eq!(regions[0].corners, quad);
    }

    /// The bug this file's fix addresses: a free (rotated) quad sitting between two
    /// horizontal lines on the page — e.g. a single word CRAFT's slope classifier
    /// misroutes, like the quoted defined term `"City"` in a real scanned ordinance
    /// page — must land between those two lines in the output order, not after
    /// both of them. Before the fix, `map_grouped_to_regions` concatenated
    /// `grouped.horizontal` then `grouped.free` unconditionally, so this free quad
    /// (vertically between the two horizontal lines) was emitted last: region
    /// order `[top line, bottom line, middle quad]` instead of
    /// `[top line, middle quad, bottom line]`.
    #[test]
    fn should_interleave_a_free_quad_between_horizontal_lines_by_position() {
        let grouped = Grouped {
            // Two horizontal lines: one near the top of the page, one near the bottom. ~keep
            horizontal: vec![[10.0, 90.0, 0.0, 20.0], [10.0, 90.0, 200.0, 220.0]],
            // A free quad vertically between the two lines (y in [100, 120]). ~keep
            free: vec![[[10.0, 100.0], [40.0, 105.0], [38.0, 120.0], [8.0, 115.0]]],
        };

        let regions = map_grouped_to_regions(grouped, 0);

        assert_eq!(regions.len(), 3, "all three regions must survive the size filter");
        let y_centers: Vec<f32> = regions
            .iter()
            .map(|region| {
                let ys: Vec<f32> = region.corners.iter().map(|c| c[1]).collect();
                0.5 * (ys.iter().cloned().fold(f32::MAX, f32::min) + ys.iter().cloned().fold(f32::MIN, f32::max))
            })
            .collect();
        assert_eq!(
            y_centers,
            vec![10.0, 110.0, 210.0],
            "the free quad (y-center 110) must sort between the top line (10) and the \
             bottom line (210), not after both -- got order {y_centers:?}"
        );
    }

    /// A taller label may have a lower center than the short glyphs beside it,
    /// while still belonging to the same visual row. The following row must not
    /// be pulled into that group merely because it overlaps the tall label.
    #[test]
    fn should_sort_mixed_height_regions_by_rows_before_left_edge() {
        let mut regions = vec![
            DetectedRegion {
                corners: [[500.0, 80.0], [550.0, 80.0], [550.0, 122.0], [500.0, 122.0]],
                axis_aligned: true,
            },
            DetectedRegion {
                corners: [[180.0, 75.0], [470.0, 75.0], [470.0, 165.0], [180.0, 165.0]],
                axis_aligned: true,
            },
            DetectedRegion {
                corners: [[80.0, 80.0], [130.0, 80.0], [130.0, 128.0], [80.0, 128.0]],
                axis_aligned: true,
            },
            DetectedRegion {
                corners: [[80.0, 126.0], [140.0, 126.0], [140.0, 156.0], [80.0, 156.0]],
                axis_aligned: true,
            },
        ];

        sort_regions_into_reading_order(&mut regions);

        let left_edges: Vec<f32> = regions
            .iter()
            .map(|region| region_geometry(&region.corners).2)
            .collect();
        assert_eq!(left_edges, vec![80.0, 180.0, 500.0, 80.0]);
    }

    #[test]
    fn should_drop_region_smaller_than_min_size() {
        // width 8, height 6 -> max extent 8 < min_size 20 -> dropped. ~keep
        let grouped = Grouped {
            horizontal: vec![[10.0, 18.0, 20.0, 26.0]],
            free: Vec::new(),
        };

        let regions = map_grouped_to_regions(grouped, 20);

        assert!(regions.is_empty());
    }

    #[test]
    fn should_drop_region_whose_extent_equals_min_size() {
        // width 20, height 6 -> max extent 20 == min_size 20 -> dropped (strict >). ~keep
        let equal = Grouped {
            horizontal: vec![[10.0, 30.0, 20.0, 26.0]],
            free: Vec::new(),
        };
        assert!(map_grouped_to_regions(equal, 20).is_empty());

        // width 21 -> max extent 21 > 20 -> kept. ~keep
        let above = Grouped {
            horizontal: vec![[10.0, 31.0, 20.0, 26.0]],
            free: Vec::new(),
        };
        assert_eq!(map_grouped_to_regions(above, 20).len(), 1);
    }

    #[test]
    fn should_run_full_pipeline_and_produce_regions() {
        // Channel-last [1, 8, 8, 2]: a solid region block (rows 1..7, cols 1..7) ~keep
        // over zero link yields one connected component past the thresholds. ~keep
        let (height, width) = (8usize, 8usize);
        let mut output = ArrayD::<f32>::zeros(IxDyn(&[1, height, width, 2]));
        for row in 1..7 {
            for col in 1..7 {
                output[[0, row, col, 0]] = 1.0;
            }
        }
        let backend = Arc::new(FixedBackend { output });
        let config = DetectionConfig {
            min_size: 0,
            ..DetectionConfig::default()
        };
        let detector = CraftDetector::new(backend, config, None);

        let image = solid_image(16, 16);
        let input = DetectorInput { image: &image };
        let regions = detector.detect(&input).expect("detection succeeds");

        assert!(!regions.regions.is_empty(), "expected at least one region");
    }

    /// End-to-end detection over a real CRAFT ONNX model.
    ///
    /// Ignored by default: it links and initializes the ONNX Runtime native
    /// library and needs a model file. Point `EASYOCR_TEST_CRAFT_ONNX` at a CRAFT
    /// detector (`craft_mlt_25k`); the detector runs over a small synthetic image
    /// and must return without error.
    #[cfg(feature = "ort")]
    #[test]
    #[ignore = "requires the ONNX Runtime native library and a CRAFT model file"]
    fn detect_over_real_craft_model() {
        let model_path =
            std::env::var("EASYOCR_TEST_CRAFT_ONNX").expect("set EASYOCR_TEST_CRAFT_ONNX to a CRAFT ONNX model path");
        let model_bytes = std::fs::read(&model_path).expect("read the model file");
        let options = crate::inference::BackendOptions {
            threads: 1,
            ..Default::default()
        };
        let backend = crate::inference::load_backend(crate::config::Backend::Ort, &model_bytes, options)
            .expect("load the CRAFT ONNX model");
        let detector = CraftDetector::new(Arc::from(backend), DetectionConfig::default(), None);

        let image = solid_image(64, 64);
        let input = DetectorInput { image: &image };
        let result = detector.detect(&input);

        assert!(result.is_ok(), "detection over the real model must succeed");
    }
}
