# Android app

The Android app is the web game in `game/`, packaged with [Capacitor](https://capacitorjs.com/) 8.5.2.
The native project lives in `android/`. App ID: `io.github.sumnoon.shologuti` (this can never change once the app is on Google Play).

The app works fully offline: three.js (r169) and the fonts are bundled in `game/vendor/`, so nothing loads from the internet.

## How the pieces fit

```
game/  ──python tools/build_web.py──▶  www/  ──npx cap sync android──▶  android/app/src/main/assets/public/  ──Gradle──▶  APK / AAB
```

- `tools/build_web.py` copies only what the game needs at runtime (no `page.html`, dev scripts or `assets/models-glb/`). About 16 MB.
- `www/` and `android/app/src/main/assets/public/` are generated and git-ignored. Edit `game/`, never those.
- Android-specific code: `android/app/src/main/java/io/github/sumnoon/shologuti/MainActivity.java` (edge to edge on every Android version, system bars hidden, screen stays on during play) and `android/app/src/main/res/` (theme, splash colour, icons). The page pads its own UI with `env(safe-area-inset-*)`, so the 3D view can fill the camera cutout.
- Icons and splash images come from `tools/make_icons.py`. Run it again if you change the icon design.

## One-time setup

1. Install **Android Studio** (it includes Java 21 and the Android SDK): https://developer.android.com/studio
   Open it once and finish the setup wizard. It downloads the SDK and asks you to accept the SDK licences.
2. In Android Studio: **More Actions → SDK Manager → SDK Platforms**, tick **Android 16 (API 36)**. On the **SDK Tools** tab, make sure *Android SDK Build-Tools* and *Android SDK Platform-Tools* are ticked. Apply.
3. In the project root: `npm install` (Capacitor packages).
4. Command-line builds need `android/local.properties` (git-ignored; Android Studio writes it when you open the project). Use forward slashes, because backslashes are escape characters in this file:
   ```
   sdk.dir=G:/Android/AndroidSdk
   ```

## Build and run a test version (debug APK)

```powershell
npm run android:sync      # rebuild www/ and copy it into android/
npm run android:open      # opens android/ in Android Studio
```

In Android Studio, plug in your phone (USB debugging on, see below) or start an emulator, then press **Run ▶**.

Command line instead of Android Studio (needs `JAVA_HOME` pointing at Android Studio's bundled Java, e.g. `$env:JAVA_HOME = 'G:\Android\Android Studio\jbr'`):

```powershell
npm run android:debug     # -> android/app/build/outputs/apk/debug/app-debug.apk
G:\Android\AndroidSdk\platform-tools\adb.exe install -r android/app/build/outputs/apk/debug/app-debug.apk
```

**USB debugging on the phone:** Settings → About phone → tap *Build number* seven times → back to Settings → System → Developer options → turn on *USB debugging*. Accept the prompt on the phone when you plug it in.

Debugging the web view: debug builds allow it automatically (release builds do not). Run the debug APK, then open `chrome://inspect` in Chrome on the PC and click *inspect* under the app.

## Release build for Google Play (signed AAB)

1. **Create an upload key once.** Keep the file and passwords safe and private (a password manager plus an offline backup). If you lose them, Google Play support has to reset the key.
   ```powershell
   cd android
   & "G:\Android\Android Studio\jbr\bin\keytool.exe" -genkeypair -v -keystore sholo-guti-upload.jks -alias upload -keyalg RSA -keysize 2048 -validity 10000
   ```
2. Create `android/keystore.properties` (git-ignored, never commit it):
   ```
   storeFile=../sholo-guti-upload.jks
   storePassword=YOUR_STORE_PASSWORD
   keyAlias=upload
   keyPassword=YOUR_KEY_PASSWORD
   ```
3. Raise the version in `android/app/build.gradle` for every upload: `versionCode` (whole number, must always increase) and `versionName` (shown to players, e.g. "1.1").
4. Build:
   ```powershell
   npm run android:release   # -> android/app/build/outputs/bundle/release/app-release.aab
   ```
   Or in Android Studio: **Build → Generate Signed App Bundle / APK**.

## Publishing on Google Play

1. Create a developer account at https://play.google.com/console (one-time fee).
2. **Create app** → name "Sholo Guti", type *Game*, *Free*.
3. Use **Play App Signing** (the default). You upload the AAB signed with your upload key; Google signs the final app.
4. Fill in the store listing: short and full description, the 512 × 512 icon (`game/assets/ui/icon-512.png`), a 1024 × 500 feature graphic, and at least two phone screenshots (`docs/screenshots/` has some).
5. App content:
   - *Data safety:* the game collects and shares no data (settings stay on the device, there are no accounts, ads or analytics).
   - *Content rating* questionnaire.
   - *Target audience.*
   - A *privacy policy* URL is still required; a short page saying no data is collected is enough. It can live on GitHub Pages.
6. Start with **Testing → Internal testing**, upload the AAB, add your own Google account as a tester and install from the link. New personal developer accounts must run a closed test with testers for a period before production access; the Play Console shows the current requirement.

## Updating the app

1. Change the game in `game/` and test it in the browser as usual.
2. `npm run android:sync`, then test on a phone.
3. Raise `versionCode` / `versionName`, `npm run android:release`, upload the new AAB.

## Performance

Measured on a Realme 8 (Mali-G76 MC4, 60 Hz screen) with the default *Battery saver* setting: 50–57 fps once running, in seat and top view, at afternoon, sunset and night. The first few seconds after launch are slower while the GPU warms up.

- Battery saver renders the 3D view at 1 CSS pixel per pixel (about 48 fps vs 35 fps at 1.5×, measured A/B on that phone). HTML text and menus stay sharp because they render at full resolution.
- Shadow settings made no measurable difference there; the remaining GPU cost is mostly the ground shader.
- The *High* setting renders at up to 2× and is meant for desktops and high-end phones.

## Known limits

- The Android back button closes the app (Capacitor default). Mapping it to the in-game menu needs the `@capacitor/app` plugin.
- iOS is not set up. Capacitor can add it (`npx cap add ios`), but building needs a Mac with Xcode.
