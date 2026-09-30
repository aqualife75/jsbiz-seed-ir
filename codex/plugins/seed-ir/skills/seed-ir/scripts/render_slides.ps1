# Export the actual generated PPTX through desktop PowerPoint when available.
# This never marks visual review as passed; a person/agent must inspect the images.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Project
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath $Project).Path
$pptxPath = [IO.Path]::GetFullPath((Join-Path $projectRoot 'output/seed-ir-draft.pptx'))
$renderRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'output/renders'))
$prefix = $projectRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
if (-not $pptxPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or -not $renderRoot.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Output path escapes the project root.'
}
if (-not (Test-Path -LiteralPath $pptxPath -PathType Leaf)) {
    throw 'output/seed-ir-draft.pptx is missing. Run render_deck.py first.'
}
# Refuse symlink/junction output paths to avoid exporting outside the selected project.
foreach ($itemPath in @((Join-Path $projectRoot 'output'), $renderRoot)) {
    if (Test-Path -LiteralPath $itemPath) {
        $item = Get-Item -LiteralPath $itemPath -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Output contains a reparse point: $itemPath" }
    }
}
New-Item -ItemType Directory -Path $renderRoot -Force | Out-Null
$ppt = $null
$presentation = $null
try {
    $ppt = New-Object -ComObject PowerPoint.Application
    # ReadOnly=true, Untitled=false, WithWindow=false. Never mutate the source deck.
    $presentation = $ppt.Presentations.Open($pptxPath, -1, 0, 0)
    $files = @()
    for ($i = 1; $i -le $presentation.Slides.Count; $i++) {
        $filename = 'slide-{0:D2}.png' -f $i
        $destination = Join-Path $renderRoot $filename
        $presentation.Slides.Item($i).Export($destination, 'PNG', 1600, 900)
        $files += 'output/renders/' + $filename
    }
    $report = [ordered]@{
        status = 'rendered-not-reviewed'
        render_method = 'powerpoint'
        pptx_sha256 = (Get-FileHash -LiteralPath $pptxPath -Algorithm SHA256).Hash.ToLowerInvariant()
        slide_count = $presentation.Slides.Count
        render_files = $files
        visual_review_passed = $false
        next_step = 'Inspect every image; record findings and review in reviews/visual.json.'
    }
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $renderRoot 'render-manifest.json') -Encoding utf8
    Write-Output ($report | ConvertTo-Json -Depth 5)
}
catch {
    Write-Error ('PowerPoint export failed. No visual pass was recorded. Open the draft in your presentation app, export each slide to PNG, and inspect the results. Cause: ' + $_.Exception.Message)
    exit 2
}
finally {
    if ($null -ne $presentation) {
        $presentation.Close()
        [Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null
    }
    if ($null -ne $ppt) {
        # Do not Quit: another presentation may belong to the user in the same COM server.
        [Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
    }
}
