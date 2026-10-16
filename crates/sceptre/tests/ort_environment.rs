#![cfg(feature = "ort")]

use std::process::Command;
use std::sync::{Arc, Barrier};

use sceptre::{Accelerator, Backend, ModelConfig, ort_environment, runtime_info_for};

const CHILD_TEST_ENV: &str = "SCEPTRE_ORT_ENVIRONMENT_CHILD_TEST";
const CONCURRENT_CALLERS: usize = 8;

fn isolated(test_name: &str, run: impl FnOnce()) {
    if std::env::var(CHILD_TEST_ENV).as_deref() == Ok(test_name) {
        run();
        return;
    }
    let output = Command::new(std::env::current_exe().expect("locate the integration test binary"))
        .args(["--exact", test_name, "--nocapture"])
        .env(CHILD_TEST_ENV, test_name)
        .output()
        .expect("run the environment regression in a fresh process");
    assert!(
        output.status.success(),
        "isolated test failed: stdout={} stderr={}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr),
    );
    assert!(String::from_utf8_lossy(&output.stdout).contains("1 passed; 0 failed"));
}

fn assert_usable_runtime() {
    let model = ModelConfig {
        backend: Backend::Ort,
        accelerator: Accelerator::Cpu,
        ..ModelConfig::default()
    };
    let runtime = runtime_info_for(&model).expect("probe the actual ONNX Runtime");
    assert_eq!(runtime.accelerator_registered, Some(Accelerator::Cpu));
    assert!(runtime.ort.is_some(), "the native ONNX Runtime must be usable");
}

#[test]
fn should_share_the_public_environment_with_runtime_probes() {
    isolated("should_share_the_public_environment_with_runtime_probes", || {
        let environment = ort_environment().expect("initialize the shared environment");
        let _builder = ort::session::Session::builder(environment).expect("create native session options");
        assert_usable_runtime();
        assert!(std::ptr::eq(
            environment,
            ort_environment().expect("reuse the environment")
        ));
    });
}

#[test]
fn should_reuse_the_environment_initialized_by_a_runtime_probe() {
    isolated("should_reuse_the_environment_initialized_by_a_runtime_probe", || {
        assert_usable_runtime();
        let environment = ort_environment().expect("reuse the runtime probe environment");
        let _builder = ort::session::Session::builder(environment).expect("create native session options");
        assert_usable_runtime();
    });
}

#[test]
fn should_initialize_one_environment_for_concurrent_callers() {
    isolated("should_initialize_one_environment_for_concurrent_callers", || {
        let barrier = Arc::new(Barrier::new(CONCURRENT_CALLERS));
        let callers: Vec<_> = (0..CONCURRENT_CALLERS)
            .map(|_| {
                let barrier = Arc::clone(&barrier);
                std::thread::spawn(move || {
                    barrier.wait();
                    let environment = ort_environment().expect("initialize or reuse the shared environment");
                    let _builder = ort::session::Session::builder(environment).expect("create native session options");
                    environment as *const ort::environment::Environment as usize
                })
            })
            .collect();
        let addresses: Vec<_> = callers
            .into_iter()
            .map(|caller| caller.join().expect("the environment caller must finish"))
            .collect();
        assert_eq!(addresses.len(), CONCURRENT_CALLERS);
        assert!(addresses.iter().all(|address| *address == addresses[0]));
        assert_usable_runtime();
    });
}

#[test]
fn should_retain_the_environment_after_session_options_are_dropped() {
    isolated(
        "should_retain_the_environment_after_session_options_are_dropped",
        || {
            let address = ort_environment().expect("initialize the shared environment") as *const _;
            for _ in 0..3 {
                let environment = ort_environment().expect("retain the environment between sessions");
                let builder = ort::session::Session::builder(environment).expect("create native session options");
                drop(builder);
                assert_eq!(environment as *const _, address);
                assert_usable_runtime();
            }
        },
    );
}

#[test]
fn should_preserve_the_duplicate_environment_error_for_uncoordinated_builders() {
    isolated(
        "should_preserve_the_duplicate_environment_error_for_uncoordinated_builders",
        || {
            let environment = ort_environment().expect("initialize the shared environment");
            let _builder = ort::session::Session::builder(environment).expect("create native session options");
            let error = ort::init()
                .build()
                .expect_err("an independent environment must remain an error");
            assert_eq!(error.message(), "only one environment is allowed per process");
            assert_usable_runtime();
        },
    );
}

#[test]
fn should_preserve_context_when_an_external_caller_initialized_an_environment() {
    isolated(
        "should_preserve_context_when_an_external_caller_initialized_an_environment",
        || {
            let environment = ort::init()
                .build()
                .expect("initialize an uncoordinated external environment");
            let _builder = ort::session::Session::builder(&environment).expect("create external session options");
            let error = ort_environment().expect_err("an external environment cannot be adopted");
            assert!(matches!(&error, sceptre::OcrError::Inference { .. }));
            assert!(error.to_string().contains("create an ONNX Runtime environment"));
            let source = std::error::Error::source(&error).expect("preserve the native error as the source");
            assert_eq!(source.to_string(), "only one environment is allowed per process");
        },
    );
}
