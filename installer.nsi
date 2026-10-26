!include "MUI2.nsh"

RequestExecutionLevel admin

!define APP_NAME "A Latee Library"
!define APP_EXE "A_Latee_Library.exe"
!define PRODUCT_VERSION "1.0.0"

Name "${APP_NAME} ${PRODUCT_VERSION}"
OutFile "Latee_Library_Installer_v1.0.exe"
Icon "assets\\app_icon.ico"
InstallDir "$PROGRAMFILES\\${APP_NAME}"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "${APP_NAME}"
  ; Ensure AppData folder has database: only install default DB if none exists
  IfFileExists "$APPDATA\\Latee Library\\library_data.db" 0 +3
    ; DB exists, skip installing default DB
    Goto db_skip
  CreateDirectory "$APPDATA\\Latee Library"
  SetOutPath "$APPDATA\\Latee Library"
  File "library_data.db"
  db_skip:

  ; Install application executable into Program Files
  SetOutPath "$INSTDIR"
  ; Copy app icon to installation folder so shortcuts can reference it directly
  File "assets\\app_icon.ico"
  File /oname=${APP_EXE} "dist\\A Latee Library.exe"

  ; Optional: add a desktop shortcut (use installed EXE as shortcut icon)
  CreateShortCut "$DESKTOP\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}" "" "$INSTDIR\\app_icon.ico" 0

  ; Optional: add a Start Menu shortcut
  CreateDirectory "$SMPROGRAMS\\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}" "" "$INSTDIR\\app_icon.ico" 0
  ; Write an uninstaller to the installation directory
  WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd

Section "Uninstall"
  ; Remove the uninstaller executable
  Delete "$INSTDIR\\Uninstall.exe"
  Delete "$DESKTOP\\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\\${APP_NAME}"
  Delete "$INSTDIR\\${APP_EXE}"
  RMDir "$INSTDIR"
SectionEnd
