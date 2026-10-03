!include "MUI2.nsh"

Name "School"
OutFile "School-Setup.exe"
InstallDir "$LOCALAPPDATA\School"
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

    ; Copy school.exe
    File "dist\school.exe"

    ; Add to PATH
    EnVar::AddValue "PATH" "$INSTDIR"
    Pop $0

    ; Run school install to register OpenCode plugin
    nsExec::ExecToStack '"$INSTDIR\school.exe" install'
    Pop $0

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Add to Programs Menu
    CreateDirectory "$SMPROGRAMS\School"
    CreateShortCut "$SMPROGRAMS\School\School.lnk" "$INSTDIR\school.exe"
    CreateShortCut "$SMPROGRAMS\School\Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    ; Run school uninstall to deregister OpenCode plugin
    nsExec::ExecToStack '"$INSTDIR\school.exe" uninstall'

    ; Remove from PATH
    EnVar::RemoveValue "PATH" "$INSTDIR"

    ; Remove files
    Delete "$INSTDIR\school.exe"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"

    ; Remove Programs Menu
    Delete "$SMPROGRAMS\School\School.lnk"
    Delete "$SMPROGRAMS\School\Uninstall.lnk"
    RMDir "$SMPROGRAMS\School"
SectionEnd
