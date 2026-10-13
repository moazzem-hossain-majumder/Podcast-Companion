# Downloads every real-world test file listed in TEST_FILES.md into .\test-files\
# with the correct extension, then makes the .aac sample from the NASA .m4a.
#
#   powershell -ExecutionPolicy Bypass -File scripts\download_test_files.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\download_test_files.ps1 -IncludeErrorCases
#
# About 245 MB in total (about 370 MB with -IncludeErrorCases). Files that already exist are skipped.
param([switch]$IncludeErrorCases)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest is very slow with the progress bar on
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12  # Windows PowerShell 5.1 may default to TLS 1.0
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'test-files'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$ua = 'PodcastCompanion-test-downloader/1.0 (https://github.com/moazzem-hossain-majumder/Podcast-Companion)'

$files = [ordered]@{
  # ---- transcript text
  'euthyphro.txt'               = 'https://www.gutenberg.org/cache/epub/1642/pg1642.txt'
  'apology.txt'                 = 'https://www.gutenberg.org/cache/epub/1656/pg1656.txt'
  'changelog-330.md'            = 'https://raw.githubusercontent.com/thechangelog/transcripts/master/podcast/the-changelog-330.md'
  'changelog-news-99.md'        = 'https://raw.githubusercontent.com/thechangelog/transcripts/master/news/changelog-news-99.md'
  'nasa-knx-interview.srt'      = 'https://images-assets.nasa.gov/video/iss063m261631434_Expedition_63_KNX_Radio_and_Chris_Cassidy_200611/iss063m261631434_Expedition_63_KNX_Radio_and_Chris_Cassidy_200611.srt'
  'nasa-epps-interviews.srt'    = 'https://images-assets.nasa.gov/video/iss061m2627771232_Live_Interviews_Jeanette_Epps_191004/iss061m2627771232_Live_Interviews_Jeanette_Epps_191004.srt'
  'nasa-internship-live.srt'    = 'https://commons.wikimedia.org/w/index.php?title=TimedText%3ANASA%20in%20Silicon%20Valley%20Live%3B%20How%20to%20Get%20an%20Internship%20at%20NASA.webm.en.srt&action=raw'
  'nasa-internship-live.vtt'    = 'https://commons.wikimedia.org/w/api.php?action=timedtext&title=File%3ANASA%20in%20Silicon%20Valley%20Live%3B%20How%20to%20Get%20an%20Internship%20at%20NASA.webm&lang=en&trackformat=vtt'
  # ---- audio
  'martin-amis-interview.mp3'   = 'https://upload.wikimedia.org/wikipedia/commons/6/61/Martin_Amis_and_creative_writing_%28Interview_1990%29.mp3'
  'nasa-hwhap-424-ai.mp3'       = 'https://images-assets.nasa.gov/audio/Ep424_AI_at_NASA/Ep424_AI_at_NASA~128k.mp3'
  'nasa-hwhap-424-ai.m4a'       = 'https://images-assets.nasa.gov/audio/Ep424_AI_at_NASA/Ep424_AI_at_NASA~64k.m4a'
  'nasa-hwhap-391-mars.m4a'     = 'https://images-assets.nasa.gov/audio/Ep391_Mars_Is_Hard/Ep391_Mars_Is_Hard~64k.m4a'
  'nasa-knx-interview.mp4'      = 'https://images-assets.nasa.gov/video/iss063m261631434_Expedition_63_KNX_Radio_and_Chris_Cassidy_200611/iss063m261631434_Expedition_63_KNX_Radio_and_Chris_Cassidy_200611~mobile.mp4'
  'roosevelt-1912-speech.wav'   = 'https://upload.wikimedia.org/wikipedia/commons/a/ab/The_Right_of_the_People_to_Rule_%28Speech_by_Theodore_Roosevelt%29.wav'
  'spoken-wikipedia-bioinformatics.ogg' = 'https://upload.wikimedia.org/wikipedia/commons/4/43/En-Bioinformatics.ogg'
  'preservapedia-podcast-mccoy.flac'    = 'https://upload.wikimedia.org/wikipedia/commons/1/10/Preservapedia_Podcast_Richard_McCoy.flac'
  'barbados-1960s-interview.webm'       = 'https://upload.wikimedia.org/wikipedia/commons/8/85/What_Barbados_was_like_in_the_1960%27s-N0d4O18lXqs.webm'
}
if ($IncludeErrorCases) {
  $files['ERROR-too-big-77MB.mp3']   = 'https://upload.wikimedia.org/wikipedia/commons/7/74/Houston_We_Have_a_Podcast_01-345_-_The_Lost_Universe.mp3'
  $files['ERROR-too-long-phaedrus.txt'] = 'https://www.gutenberg.org/cache/epub/1636/pg1636.txt'
  $files['spanish-big-bang.flac']    = 'https://upload.wikimedia.org/wikipedia/commons/c/ca/Big_bang_introduction_article_wikipedia_spanish.flac'
}

$failed = @()
foreach ($name in $files.Keys) {
  $dest = Join-Path $out $name
  if (Test-Path $dest) { Write-Host "skip  $name (already downloaded)"; continue }
  Write-Host -NoNewline "get   $name ... "
  try {
    Invoke-WebRequest -Uri $files[$name] -OutFile $dest -UserAgent $ua -UseBasicParsing -TimeoutSec 600
    Write-Host ("{0:N1} MB" -f ((Get-Item $dest).Length / 1MB))
  } catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    if (Test-Path $dest) { Remove-Item $dest }
    $failed += $name
  }
}

# ---- .aac: lossless stream copy of the NASA podcast's AAC audio into a raw ADTS file
$m4a = Join-Path $out 'nasa-hwhap-424-ai.m4a'
$aac = Join-Path $out 'nasa-hwhap-424-ai.aac'
if ((Test-Path $m4a) -and -not (Test-Path $aac)) {
  $py = Join-Path $root '.venv\Scripts\python.exe'
  if (-not (Test-Path $py)) { $py = 'python' }
  try {
    $ffmpeg = & $py -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
    & $ffmpeg -hide_banner -loglevel error -y -i $m4a -vn -c:a copy -f adts $aac
    if ($LASTEXITCODE -ne 0) { throw "ffmpeg exited with code $LASTEXITCODE" }
    Write-Host ("made  nasa-hwhap-424-ai.aac  {0:N1} MB (from the .m4a, no re-encoding)" -f ((Get-Item $aac).Length / 1MB))
  } catch {
    Write-Host "Could not make the .aac (is the project's .venv set up?): $($_.Exception.Message)" -ForegroundColor Yellow
    $failed += 'nasa-hwhap-424-ai.aac'
  }
}

Write-Host ""
Write-Host "Saved to: $out"
if ($failed.Count) { Write-Host "Failed: $($failed -join ', ')  (re-run the script to retry)" -ForegroundColor Red; exit 1 }
Write-Host "All test files ready. Open http://127.0.0.1:8000 and drag them into the matching tab."
