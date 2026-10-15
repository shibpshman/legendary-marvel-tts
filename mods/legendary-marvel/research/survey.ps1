$out = 'C:\Users\steph\survey_out.txt'
$src = 'E:\Media\Board Games\Marvel Legendary Cards'
$docs = [Environment]::GetFolderPath('MyDocuments')
$tts  = Join-Path $docs 'My Games\Tabletop Simulator\Mods'
Add-Type -AssemblyName System.Drawing

& {
  "=== SOURCE: $src (exists: $(Test-Path $src))"
  "--- top-level folders, file counts"
  Get-ChildItem $src -Directory | ForEach-Object {
    "{0,6}  {1}" -f (Get-ChildItem $_.FullName -File -Recurse).Count, $_.Name
  }
  "--- files directly in root: $((Get-ChildItem $src -File).Count)"

  "--- extensions"
  Get-ChildItem $src -File -Recurse | Group-Object Extension | ForEach-Object {
    "{0,-8} {1,7} files  {2,8} GB" -f $_.Name, $_.Count, [math]::Round(($_.Group | Measure-Object Length -Sum).Sum/1GB,2)
  }

  "--- first 40 file paths"
  Get-ChildItem $src -File -Recurse | Select-Object -First 40 -ExpandProperty FullName

  "--- 15 random image dimensions"
  Get-ChildItem $src -File -Recurse | Where-Object { $_.Extension -match '\.(png|jpe?g)$' } |
    Get-Random -Count 15 | ForEach-Object {
      try { $i=[System.Drawing.Image]::FromFile($_.FullName); "{0}x{1}  {2}" -f $i.Width,$i.Height,$_.FullName; $i.Dispose() }
      catch { "unreadable: $($_.FullName)" }
    }

  ""
  "=== TTS: $tts (exists: $(Test-Path $tts))"
  $img = Join-Path $tts 'Images'
  "--- Images cache"
  Get-ChildItem $img -File | Measure-Object Length -Sum | ForEach-Object { "{0} files, {1} GB" -f $_.Count, [math]::Round($_.Sum/1GB,2) }
  Get-ChildItem $img -File | Sort-Object LastWriteTime -Descending | Select-Object -First 10 | ForEach-Object { "{0}  {1}  {2}" -f $_.LastWriteTime, $_.Length, $_.Name }

  "--- Workshop folder"
  Get-ChildItem (Join-Path $tts 'Workshop') -Filter *.json | ForEach-Object { "{0,8} MB  {1}" -f [math]::Round($_.Length/1MB,2), $_.Name }

  "--- Legendary matches in WorkshopFileInfos.json"
  $wfi = Join-Path $tts 'Workshop\WorkshopFileInfos.json'
  if (Test-Path $wfi) { Select-String -Path $wfi -Pattern 'legendary' -Context 2,2 | ForEach-Object { $_.ToString() } }
} *> $out

"Done: $out"