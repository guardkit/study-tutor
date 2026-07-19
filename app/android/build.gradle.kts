allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

// TODO: drop once flutter_appauth stops pinning compileSdkVersion 31 — 8.0.3's
// android/build.gradle hardcodes it, but its androidx dependencies require
// compileSdk >= 34, failing checkDebugAarMetadata under AGP 9.
// Raise only modules pinned below 34; the app itself uses flutter.compileSdkVersion.
subprojects {
    val raiseCompileSdk: (Project) -> Unit = { p ->
        val android = p.extensions.findByName("android")
        if (android is com.android.build.api.dsl.LibraryExtension) {
            val sdk = android.compileSdk
            if (sdk != null && sdk < 34) {
                android.compileSdk = 36
            }
        }
    }
    if (state.executed) raiseCompileSdk(this) else afterEvaluate { raiseCompileSdk(this) }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
