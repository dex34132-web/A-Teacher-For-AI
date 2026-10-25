!include "MUI2.nsh"

Name "Toolio"
OutFile "Toolio-Setup.exe"
InstallDir "$LOCALAPPDATA\Toolio"
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

    ; Copy toolio.exe
    File "dist\toolio.exe"

    ; Add to PATH
    EnVar::AddValue "PATH" "$INSTDIR"
    Pop $0

    ; Run toolio install to register OpenCode plugin
    nsExec::ExecToStack '"$INSTDIR\toolio.exe" install'
    Pop $0

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Add to Programs Menu
    CreateDirectory "$SMPROGRAMS\Toolio"
    CreateShortCut "$SMPROGRAMS\Toolio\Toolio.lnk" "$INSTDIR\toolio.exe"
    CreateShortCut "$SMPROGRAMS\Toolio\Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    ; Run toolio uninstall to deregister OpenCode plugin
    nsExec::ExecToStack '"$INSTDIR\toolio.exe" uninstall'

    ; Remove from PATH
    EnVar::RemoveValue "PATH" "$INSTDIR"

    ; Remove files
    Delete "$INSTDIR\toolio.exe"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"

    ; Remove Programs Menu
    Delete "$SMPROGRAMS\Toolio\Toolio.lnk"
    Delete "$SMPROGRAMS\Toolio\Uninstall.lnk"
    RMDir "$SMPROGRAMS\Toolio"
SectionEnd
