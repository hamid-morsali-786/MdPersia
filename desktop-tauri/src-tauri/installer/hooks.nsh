; Register an Open With handler without overwriting Windows UserChoice.
!macro NSIS_HOOK_POSTINSTALL
  WriteRegStr HKCU "Software\Classes\MdPersia.Markdown" "" "Markdown Document (MdPersia)"
  WriteRegStr HKCU "Software\Classes\MdPersia.Markdown\DefaultIcon" "" '"$INSTDIR\MdPersia.exe",0'
  WriteRegStr HKCU "Software\Classes\MdPersia.Markdown\shell\open\command" "" '"$INSTDIR\MdPersia.exe" "%1"'
  WriteRegStr HKCU "Software\Classes\.md\OpenWithProgids" "MdPersia.Markdown" ""
  WriteRegStr HKCU "Software\Classes\.markdown\OpenWithProgids" "MdPersia.Markdown" ""
  WriteRegStr HKCU "Software\MdPersia\Capabilities" "ApplicationName" "MdPersia"
  WriteRegStr HKCU "Software\MdPersia\Capabilities" "ApplicationDescription" "Persian Markdown reader, editor and converter"
  WriteRegStr HKCU "Software\MdPersia\Capabilities\FileAssociations" ".md" "MdPersia.Markdown"
  WriteRegStr HKCU "Software\MdPersia\Capabilities\FileAssociations" ".markdown" "MdPersia.Markdown"
  WriteRegStr HKCU "Software\RegisteredApplications" "MdPersia" "Software\MdPersia\Capabilities"
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
  ReadRegStr $0 HKCU "Software\Classes\MdPersia.Markdown\shell\open\command" ""
  ${If} $0 == '"$INSTDIR\MdPersia.exe" "%1"'
    DeleteRegKey HKCU "Software\Classes\MdPersia.Markdown"
    DeleteRegValue HKCU "Software\Classes\.md\OpenWithProgids" "MdPersia.Markdown"
    DeleteRegValue HKCU "Software\Classes\.markdown\OpenWithProgids" "MdPersia.Markdown"
    DeleteRegValue HKCU "Software\RegisteredApplications" "MdPersia"
    DeleteRegKey HKCU "Software\MdPersia\Capabilities"
  ${EndIf}
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
!macroend
