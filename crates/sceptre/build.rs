use std::{env, path::PathBuf, process::Command};

fn main() -> Result<(), String> {
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-env-changed=CC");
    println!("cargo:rerun-if-env-changed=DEVELOPER_DIR");
    println!("cargo:rerun-if-env-changed=SDKROOT");
    if env::var("CARGO_CFG_TARGET_OS").as_deref() != Ok("macos")
        || env::var_os("CARGO_FEATURE_ORT_BUNDLED").is_none()
        || env::var_os("CARGO_FEATURE_ORT_DYNAMIC").is_some()
    {
        return Ok(());
    }

    // ort-sys rc.14 omits compiler-rt; see adrs/0047-macos-bundled-ort-compiler-runtime.md. ~keep
    let compiler = env::var_os("CC").unwrap_or_else(|| "clang".into());
    let output = Command::new(&compiler)
        .arg("--print-file-name=libclang_rt.osx.a")
        .output()
        .map_err(|error| format!("locating macOS compiler runtime with {compiler:?}: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "locating macOS compiler runtime with {compiler:?}: {}: {}",
            output.status,
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    let path = PathBuf::from(String::from_utf8_lossy(&output.stdout).trim());
    if !path.is_absolute() || !path.is_file() {
        return Err(format!(
            "locating macOS compiler runtime with {compiler:?}: archive not found at {}",
            path.display()
        ));
    }
    let directory = path.parent().ok_or_else(|| {
        format!(
            "locating macOS compiler runtime: archive has no directory: {}",
            path.display()
        )
    })?;
    println!("cargo:rustc-link-search=native={}", directory.display());
    println!("cargo:rustc-link-lib=static=clang_rt.osx");
    Ok(())
}
