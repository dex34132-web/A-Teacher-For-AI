!include "MUI2.nsh"

Name "Teacher"
OutFile "Teacher-Setup.exe"
InstallDir "$LOCALAPPDATA\Teacher"
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

    ; Copy teacher.exe
    File "dist\teacher.exe"

    ; Add to PATH
    EnVar::AddValue "PATH" "$INSTDIR"
    Pop $0

    ; Run teacher install to register OpenCode plugin
    nsExec::ExecToStack '"$INSTDIR\teacher.exe" install'
    Pop $0

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Add to Programs Menu
    CreateDirectory "$SMPROGRAMS\Teacher"
    CreateShortCut "$SMPROGRAMS\Teacher\Teacher.lnk" "$INSTDIR\teacher.exe"
    CreateShortCut "$SMPROGRAMS\Teacher\Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    ; Run teacher uninstall to deregister OpenCode plugin
    nsExec::ExecToStack '"$INSTDIR\teacher.exe" uninstall'

    ; Remove from PATH
    EnVar::RemoveValue "PATH" "$INSTDIR"

    ; Remove files
    Delete "$INSTDIR\teacher.exe"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"

    ; Remove Programs Menu
    Delete "$SMPROGRAMS\Teacher\Teacher.lnk"
    Delete "$SMPROGRAMS\Teacher\Uninstall.lnk"
    RMDir "$SMPROGRAMS\Teacher"
SectionEnd
