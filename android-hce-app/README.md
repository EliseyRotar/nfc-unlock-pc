# NFC Unlock Companion (Android)

A tiny Host Card Emulation (HCE) app. It has exactly one job: when the phone
is held against the ACR122U, answer with a 16-byte token so
`src/nfc_unlock/reader.py` (running on the PC) can recognize this specific
phone.

There's no server, no Bluetooth, no account, no network permission at all.

## Building

This is a standard Gradle/Android project - open the `android-hce-app/`
folder in Android Studio (Hedgehog or newer) and hit Run, or build from the
command line if you have the Android SDK + a Gradle install:

```bash
gradle assembleDebug
# APK lands in app/build/outputs/apk/debug/app-debug.apk
```

(No Gradle wrapper is checked in to keep the repo small - use your own
`gradle` or generate a wrapper with `gradle wrapper`.)

## How it works

1. `app/src/main/res/xml/apduservice.xml` registers this app as a card
   emulator for AID `F0AC1DC0DE0001` (an unregistered/proprietary AID -
   it won't conflict with payment cards, transit cards, etc).
2. `TokenStore.kt` generates a random 16-byte token the first time the app
   runs and stores it in SharedPreferences.
3. `HceService.kt` (a `HostApduService`) answers any `SELECT` for that AID
   with the token bytes + status `90 00`.
4. On the PC, `reader.get_hce_token()` SELECTs that AID and gets the token
   back as a hex string - this is the phone's "identifier" for enrollment
   and unlock, exactly like a physical tag's UID.

Android randomizes the *card UID* it presents over HCE for privacy on every
tap, which is why we don't use that - the token is the real, stable secret.

## Re-enrolling after regenerating a token

If you tap "Generate new token" in the app, the old token stops working.
Re-run `python src/main.py enroll` on the PC and tap the phone again.
