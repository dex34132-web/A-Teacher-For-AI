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

    ; Check Python
    nsExec::ExecToStack 'python --version'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_OK "Python 3.11+ is required but not found.$\n$\nPlease install Python from https://www.python.org/downloads/"
        Abort
    ${EndIf}

    ; Install Lerev via pip
    nsExec::ExecToStack 'pip install lerev'
    Pop $0
    ${If} $0 != 0
        MessageBox MB_OK "Failed to install Lerev via pip.$\n$\nPlease check your Python installation."
        Abort
    ${EndIf}

    ; Run lerev install
    nsExec::ExecToStack 'lerev install'
    Pop $0

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Add to PATH (per-user)
    EnVar::AddValue "PATH" "$INSTDIR"
SectionEnd

Section "Uninstall"
    ; Run lerev uninstall
    nsExec::ExecToStack 'lerev uninstall'

    ; Remove from PATH
    EnVar::RemoveValue "PATH" "$INSTDIR"

    ; Remove files
    RMDir /r "$INSTDIR"
    Delete "$INSTDIR\uninstall.exe"
SectionEnd
