//! CRAFT text-detection configuration.
//!
//! Defaults mirror EasyOCR's `readtext` detection parameters, except `width_ths`
//! (see its documentation for the measurements behind the deviation).

use serde::{Deserialize, Serialize};

use crate::error::{OcrError, Result};

/// Parameters controlling CRAFT detection and box grouping.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct DetectionConfig {
    /// Text confidence threshold (region score). EasyOCR default `0.7`.
    pub text_threshold: f32,
    /// Link confidence threshold (affinity score). EasyOCR default `0.4`.
    pub link_threshold: f32,
    /// Low-bound text score for region growth. EasyOCR default `0.4`.
    pub low_text: f32,
    /// Maximum image dimension before down-scaling. EasyOCR default `2560`.
    pub canvas_size: u32,
    /// Magnification ratio applied before detection. EasyOCR default `1.0`.
    pub mag_ratio: f32,
    /// Minimum box size (px) to keep. EasyOCR default `20`.
    pub min_size: u32,
    /// Slope threshold for splitting horizontal vs. free boxes. Default `0.1`.
    pub slope_ths: f32,
    /// Vertical-center threshold for line merging. Default `0.5`.
    pub ycenter_ths: f32,
    /// Height threshold for line merging. Default `0.5`.
    pub height_ths: f32,
    /// Width threshold for line merging, as a multiple of box height. Default `1.0`.
    ///
    /// Two horizontally adjacent boxes on the same line merge into one text line
    /// only when the gap between them is smaller than `width_ths` times the box
    /// height. Raising it merges across wider gaps, so a line is assembled from
    /// more boxes and fewer one-word lines are emitted; lowering it fragments
    /// lines. The ceiling is the two-column gutter — set high enough and the last
    /// word of one column merges with the first word of the next, which corrupts
    /// reading order and loses text.
    ///
    /// Deliberately much wider than EasyOCR's `0.5`, which the other defaults here
    /// still mirror. At `0.5` a letter-spaced all-caps heading exceeds the gap test
    /// and surfaces one word per line. Two rounds of measurement are on record, and
    /// they do not compose into a validated case for `3.0`:
    ///
    /// - **`0.5` -> `1.0`** (the original widening): measured over scanned fixtures
    ///   as line count / one-word-line count. A 16-page ordinance went `417/136` ->
    ///   `339/85`, a two-column paper `1510/799` -> `1297/669`, an academic scan
    ///   `151/55` -> `135/51`, with recognized word counts flat or slightly up in
    ///   every case. `1.5` and `2.0` were also measured on the same two-column paper
    ///   and rejected: they merge across the gutter and start losing text
    ///   (`4974` -> `4923` -> `4895` words).
    /// - **`1.0` -> `3.0`** (the current default): measured only on the
    ///   `ordinance_2197_scanned` fixture's list-structure score, `0.361` ->
    ///   `0.644`, with four other swept fixtures unchanged. This sweep did not
    ///   reproduce the `1.5`/`2.0` gutter-merge regression on the two-column
    ///   fixture at `3.0`, but the text-loss word counts the earlier round tracked
    ///   were not re-measured.
    ///
    /// - **`0.5` -> `3.0`** (2026-08-20): swept `0.5 / 1.0 / 1.5 / 2.0 / 3.0` over all
    ///   seven scanned fixtures, scoring recognized word count and one-word-line count.
    ///   Corpus totals (words / one-word lines): `0.5` 12959/596, `1.0` 12945/501, `1.5`
    ///   12894/471, `2.0` 12868/443, `3.0` 12862/402. Marginal cost in words per
    ///   one-word-line removed: `0.15` for `0.5`->`1.0`, `1.70` for `1.0`->`1.5`, `0.93`
    ///   for `1.5`->`2.0`, `0.15` for `2.0`->`3.0`. So `1.0` is the knee, and the
    ///   `1.0`-`2.0` band is the worst trade on offer.
    ///
    /// - **CJK golden parity** (2026-08-20) is what settles the upper bound, and it
    ///   REFUTES `3.0`. That scanned corpus is almost entirely single-column, so it
    ///   under-weights the gutter case. Swept against the three CJK golden fixtures and
    ///   scored against the authoritative EasyOCR reference:
    ///
    ///   | fixture        | 0.5 | 1.0 | 1.5 | 2.0 | 3.0 |
    ///   |----------------|-----|-----|-----|-----|-----|
    ///   | `chinese.jpg`  | ok  | ok  | ok  | ok  | merges `W` + `Yuyuan Rd` |
    ///   | `korean.png`   | ok  | ok  | breaks | breaks | breaks |
    ///   | `japanese.jpg` | ok  | ok  | ok  | ok  | ok |
    ///
    ///   `korean.png` is a two-column sign. At `1.5` and above the columns merge across
    ///   the gutter -- six lines collapse to four, then three -- and the distance
    ///   degrades from `2O5Km` to `25Km`, losing a digit outright. `1.0` is therefore
    ///   the highest value that keeps every CJK golden, and at `1.0` `korean.png`
    ///   matches the EasyOCR reference exactly.
    ///
    /// Net: `1.0`. Both lines of evidence agree, and it is the value the earlier
    /// measured round already chose. The `3.0` that briefly replaced it was committed
    /// with a fabricated rationale and broke two of the three CJK goldens; those tests
    /// did not catch it because they skip unless `SCEPTRE_REQUIRE_MODELS` is set with
    /// the models cached, and the commits were never pushed. The upper bound is also
    /// pinned by a synthetic-geometry unit test
    /// (`should_never_merge_boxes_across_a_gutter_sized_gap` in `detect/group.rs`),
    /// which uses a ratio-5.0 gap and so excludes nothing in `[1.67, 5.0)` -- the CJK
    /// goldens are the real bound.
    pub width_ths: f32,
    /// Fractional margin added around each box. Default `0.1`.
    pub add_margin: f32,
    /// Enable a whole-page orientation pre-pass: probe 0/90/180/270° rotations
    /// at [`orientation_probe_canvas_size`](Self::orientation_probe_canvas_size)
    /// and run the real detection pass on the best-scoring rotation instead of
    /// the page as given. Off by default: it is a net accuracy win on rotated
    /// pages but carries a small false-positive risk on small, dense-glyph
    /// script images (see ADR 0037) and a latency cost from the extra probe
    /// passes, so it is opt-in rather than silently changing default behavior.
    /// EasyOCR has no equivalent.
    pub detect_orientation: bool,
    /// Canvas size (px) used for each of the four orientation probe passes when
    /// [`detect_orientation`](Self::detect_orientation) is enabled. Smaller than
    /// `canvas_size` to keep the pre-pass cheap. Default `1280`.
    pub orientation_probe_canvas_size: u32,
    /// Minimum relative improvement a rotation's score must have over the
    /// unrotated (0°) score before the pre-pass switches away from it, guarding
    /// against flipping an already-upright page on a marginal score difference.
    /// Default `0.05` (5%).
    pub orientation_margin: f32,
    /// Opt-in cap on the padded detection input's area, in megapixels.
    ///
    /// Peak memory during detection tracks the padded CRAFT input's area, not its
    /// longest side (see ADR 0041), so this bounds memory directly where
    /// [`canvas_size`](Self::canvas_size) only bounds it indirectly. When set, it
    /// further constrains the resize target computed from `canvas_size` and
    /// `mag_ratio` so the padded (multiple-of-32) input area stays within the
    /// budget; the effective canvas is the minimum of what `canvas_size` and this
    /// budget each allow. `None` (the default) leaves detection input sizing
    /// exactly as `canvas_size`/`mag_ratio` compute it today.
    pub max_megapixels: Option<f32>,
}

impl Default for DetectionConfig {
    fn default() -> Self {
        Self {
            text_threshold: 0.7,
            link_threshold: 0.4,
            low_text: 0.4,
            canvas_size: 2560,
            mag_ratio: 1.0,
            min_size: 20,
            slope_ths: 0.1,
            ycenter_ths: 0.5,
            height_ths: 0.5,
            width_ths: 1.0,
            add_margin: 0.1,
            detect_orientation: false,
            orientation_probe_canvas_size: 1280,
            orientation_margin: 0.05,
            max_megapixels: None,
        }
    }
}

impl DetectionConfig {
    /// Validate detection settings consumed by the engine.
    pub(crate) fn validate(&self) -> Result<()> {
        if let Some(max_megapixels) = self.max_megapixels {
            let valid = max_megapixels.is_finite() && max_megapixels > 0.0;
            if !valid {
                return Err(OcrError::config(format!(
                    "detection.max_megapixels must be finite and greater than 0, got {max_megapixels}"
                )));
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `width_ths` is the one detection default that deliberately departs from
    /// EasyOCR's `0.5`. Pinned because narrowing it silently restores the
    /// one-word-per-line splitting on letter-spaced headings, which is invisible in
    /// any single-box unit test -- and because WIDENING it past `1.0` merges across a
    /// two-column gutter, which `korean.png`'s golden catches and no unit test does.
    ///
    /// `1.0` is the highest value that keeps all three CJK goldens (see the field's
    /// doc comment for the sweep). `1.5` and above collapse `korean.png`'s two columns
    /// and lose a digit; `3.0` additionally merges `chinese.jpg`'s `W` + `Yuyuan Rd`.
    #[test]
    fn should_default_width_ths_wider_than_easyocr_to_avoid_splitting_letter_spaced_lines() {
        assert_eq!(DetectionConfig::default().width_ths, 1.0);
    }

    /// `width_ths` is a plain configurable field, not a hardcoded constant: a
    /// caller-set value must survive a serialize/deserialize round trip rather
    /// than snapping back to the default.
    #[test]
    fn should_round_trip_a_non_default_width_ths_through_json() {
        // 2.5, deliberately: the value must DIFFER from the default or the assertion
        // passes whether or not the round trip preserved anything.
        assert_ne!(
            DetectionConfig::default().width_ths,
            2.5,
            "the probe value must not be the default"
        );
        let config = DetectionConfig {
            width_ths: 2.5,
            ..DetectionConfig::default()
        };

        let json = serde_json::to_string(&config).expect("serialize");
        let restored: DetectionConfig = serde_json::from_str(&json).expect("deserialize");

        assert_eq!(restored.width_ths, 2.5);
    }

    #[test]
    fn should_default_orientation_pre_pass_to_disabled() {
        let config = DetectionConfig::default();
        assert!(!config.detect_orientation);
        assert_eq!(config.orientation_probe_canvas_size, 1280);
        assert_eq!(config.orientation_margin, 0.05);
    }

    #[test]
    fn should_default_max_megapixels_to_none() {
        let config = DetectionConfig::default();
        assert_eq!(config.max_megapixels, None);
    }

    #[test]
    fn should_accept_absent_max_megapixels() {
        let config = DetectionConfig {
            max_megapixels: None,
            ..DetectionConfig::default()
        };
        config.validate().expect("no budget is always valid");
    }

    #[test]
    fn should_accept_a_positive_finite_max_megapixels() {
        let config = DetectionConfig {
            max_megapixels: Some(4.0),
            ..DetectionConfig::default()
        };
        config.validate().expect("a positive finite budget is valid");
    }

    #[test]
    fn should_reject_zero_max_megapixels() {
        let config = DetectionConfig {
            max_megapixels: Some(0.0),
            ..DetectionConfig::default()
        };
        let error = config.validate().expect_err("zero budget must be rejected");
        assert!(error.to_string().contains("max_megapixels"));
    }

    #[test]
    fn should_reject_negative_max_megapixels() {
        let config = DetectionConfig {
            max_megapixels: Some(-1.0),
            ..DetectionConfig::default()
        };
        assert!(config.validate().is_err());
    }

    #[test]
    fn should_reject_nan_max_megapixels() {
        let config = DetectionConfig {
            max_megapixels: Some(f32::NAN),
            ..DetectionConfig::default()
        };
        assert!(config.validate().is_err());
    }

    #[test]
    fn should_reject_infinite_max_megapixels() {
        let config = DetectionConfig {
            max_megapixels: Some(f32::INFINITY),
            ..DetectionConfig::default()
        };
        assert!(config.validate().is_err());
    }

    #[test]
    fn should_round_trip_orientation_fields_through_json() {
        let config = DetectionConfig {
            detect_orientation: true,
            orientation_probe_canvas_size: 640,
            orientation_margin: 0.1,
            ..DetectionConfig::default()
        };

        let json = serde_json::to_string(&config).expect("serialize");
        let restored: DetectionConfig = serde_json::from_str(&json).expect("deserialize");

        assert!(restored.detect_orientation);
        assert_eq!(restored.orientation_probe_canvas_size, 640);
        assert_eq!(restored.orientation_margin, 0.1);
    }

    #[test]
    fn should_round_trip_max_megapixels_through_json() {
        let config = DetectionConfig {
            max_megapixels: Some(6.5),
            ..DetectionConfig::default()
        };

        let json = serde_json::to_string(&config).expect("serialize");
        let restored: DetectionConfig = serde_json::from_str(&json).expect("deserialize");

        assert_eq!(restored.max_megapixels, Some(6.5));
    }

    #[test]
    fn should_reject_unknown_fields() {
        let json = r#"{"detect_orientation": true, "bogus_field": 1}"#;
        let error = serde_json::from_str::<DetectionConfig>(json).expect_err("unknown field must be rejected");
        assert!(error.to_string().contains("bogus_field"));
    }
}
