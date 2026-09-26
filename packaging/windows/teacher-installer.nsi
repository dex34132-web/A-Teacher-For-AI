!include "MUI2.nsh"

Name "Lerev"
OutFile "Lerev-Setup.exe"
InstallDir "$LOCALAPPDATA\Lerev"
RequestExecutionLevel user

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "$INSTDIR"

    ; Copy lerev.exe
    File "dist\lerev.exe"

    ; Add to PATH
    EnVar::AddValue "PATH" "$INSTDIR"
    Pop $0

    ; Run lerev install to register OpenCode plugin
    nsExec::ExecToStack '"$INSTDIR\lerev.exe" install'
    Pop $0

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Add to Programs Menu
    CreateDirectory "$SMPROGRAMS\Lerev"
    CreateShortCut "$SMPROGRAMS\Lerev\Lerev.lnk" "$INSTDIR\lerev.exe"
    CreateShortCut "$SMPROGRAMS\Lerev\Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    ; Run lerev uninstall to deregister OpenCode plugin
    nsExec::ExecToStack '"$INSTDIR\lerev.exe" uninstall'

    ; Remove from PATH
    EnVar::RemoveValue "PATH" "$INSTDIR"

    ; Remove files
    Delete "$INSTDIR\lerev.exe"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"

    ; Remove Programs Menu
    Delete "$SMPROGRAMS\Lerev\Lerev.lnk"
    Delete "$SMPROGRAMS\Lerev\Uninstall.lnk"
    RMDir "$SMPROGRAMS\Lerev"
SectionEnd
