[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Instructions,
    [Parameter(Mandatory = $true)][string]$Output,
    [string]$CleanOutput,
    [string]$Author = "合同审核AI",
    [ValidateSet("comment", "revision", "revision_comment")][string]$DefaultMode = "revision_comment",
    [string]$Date,
    [string]$InternalScriptRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:EffectiveScriptRoot = if (-not [string]::IsNullOrWhiteSpace($InternalScriptRoot)) {
    $InternalScriptRoot
} elseif (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $PSScriptRoot
} elseif (-not [string]::IsNullOrWhiteSpace($PSCommandPath)) {
    Split-Path -Parent $PSCommandPath
} else {
    (Get-Location).Path
}

$script:W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
$script:PR = "http://schemas.openxmlformats.org/package/2006/relationships"
$script:CT = "http://schemas.openxmlformats.org/package/2006/content-types"
$script:XML = "http://www.w3.org/XML/1998/namespace"
$script:CommentsRel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
$script:SettingsRel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings"
$script:CommentsType = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
$script:SettingsType = "application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"
$script:CommentFontName = "SimSun"

function FullPath([string]$PathText) { [System.IO.Path]::GetFullPath($PathText) }
function HasNonAscii([AllowNull()][string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    foreach ($char in $Text.ToCharArray()) {
        if ([int][char]$char -gt 127) { return $true }
    }
    $false
}
function Norm([AllowNull()][string]$Text) { if ($null -eq $Text) { "" } else { ([regex]::Replace($Text, "\s+", " ")).Trim() } }
function Iso([AllowNull()][string]$Value) { if ([string]::IsNullOrWhiteSpace($Value)) { [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ") } else { $Value } }

function Ensure-DotNetCompression {
    Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop
    Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop
}

function LoadXml([string]$Path) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.PreserveWhitespace = $true
    $doc.Load($Path)
    $doc
}

function SaveXml([System.Xml.XmlDocument]$Doc, [string]$Path) {
    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Encoding = New-Object System.Text.UTF8Encoding($true)
    $settings.Indent = $false
    $writer = [System.Xml.XmlWriter]::Create($Path, $settings)
    try { $Doc.Save($writer) } finally { $writer.Dispose() }
}

function Ns([System.Xml.XmlDocument]$Doc) {
    $ns = New-Object System.Xml.XmlNamespaceManager($Doc.NameTable)
    $ns.AddNamespace("w", $script:W)
    $ns.AddNamespace("pr", $script:PR)
    $ns.AddNamespace("ct", $script:CT)
    $ns
}

function SelectNodesNs($XmlObject, [string]$XPath) {
    $results = @(Select-Xml -Xml $XmlObject -XPath $XPath -Namespace @{ w = $script:W; pr = $script:PR; ct = $script:CT } | ForEach-Object { $_.Node })
    return ,$results
}

function SelectOneNs($XmlObject, [string]$XPath) {
    $nodes = @(SelectNodesNs -XmlObject $XmlObject -XPath $XPath)
    if ($nodes.Length -gt 0) { $nodes[0] } else { $null }
}

function SharedBytes([string]$Path) {
    $share = [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, $share)
    try {
        $memory = New-Object System.IO.MemoryStream
        try { $stream.CopyTo($memory); $memory.ToArray() } finally { $memory.Dispose() }
    }
    finally { $stream.Dispose() }
}

function CopyDocx([string]$From, [string]$To) {
    $parent = Split-Path -Parent $To
    if ($parent) { [System.IO.Directory]::CreateDirectory($parent) | Out-Null }
    [System.IO.File]::WriteAllBytes($To, (SharedBytes $From))
}

function Use-Staging([string[]]$Paths) {
    foreach ($path in @($Paths)) {
        if (HasNonAscii $path) { return $true }
    }
    $false
}

function Invoke-Staging([string]$SourcePath, [string]$InstructionsPath) {
    $stagingScript = Join-Path $script:EffectiveScriptRoot "internal_stage_review_inputs.ps1"
    if (-not (Test-Path -LiteralPath $stagingScript)) {
        throw "缺少 staging 脚本: $stagingScript"
    }

    $raw = & $stagingScript -SourcePath $SourcePath -InstructionsPath $InstructionsPath | Out-String
    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "staging 脚本未返回结果: $stagingScript"
    }

    $stage = $raw | ConvertFrom-Json
    foreach ($field in @("workspace_root", "staged_source", "staged_instructions", "staged_reviewed_docx", "staged_clean_docx")) {
        if ($null -eq $stage.PSObject.Properties[$field] -or [string]::IsNullOrWhiteSpace([string]$stage.$field)) {
            throw "staging 输出缺少字段 ${field}: $stagingScript"
        }
    }
    $stage
}

function Read-JsonFile([string]$Path) {
    Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function NewDoc([string]$LocalName, [string]$NsUri, [string]$Prefix) {
    $doc = New-Object System.Xml.XmlDocument
    [void]$doc.AppendChild($doc.CreateXmlDeclaration("1.0", "UTF-8", $null))
    $root = if ($Prefix) { $doc.CreateElement($Prefix, $LocalName, $NsUri) } else { $doc.CreateElement($LocalName, $NsUri) }
    [void]$doc.AppendChild($root)
    $doc
}

function WNode([System.Xml.XmlDocument]$Doc, [string]$Name) { $Doc.CreateElement("w", $Name, $script:W) }
function SetWAttr([System.Xml.XmlElement]$Node, [string]$Name, [string]$Value) {
    $attr = $Node.OwnerDocument.CreateAttribute("w", $Name, $script:W)
    $attr.Value = $Value
    [void]$Node.Attributes.Append($attr)
}

function AddCommentFontProps([System.Xml.XmlElement]$RunProps) {
    $fonts = WNode $RunProps.OwnerDocument "rFonts"
    SetWAttr $fonts "ascii" $script:CommentFontName
    SetWAttr $fonts "hAnsi" $script:CommentFontName
    SetWAttr $fonts "eastAsia" $script:CommentFontName
    SetWAttr $fonts "cs" $script:CommentFontName
    SetWAttr $fonts "hint" "eastAsia"
    [void]$RunProps.AppendChild($fonts)
}

function NextId([string[]]$Values) {
    $max = -1
    foreach ($value in $Values) { if ($value -match '^\d+$') { $n = [int]$value; if ($n -gt $max) { $max = $n } } }
    $max + 1
}

function RunPropsClone([System.Xml.XmlNode]$Paragraph) {
    $node = SelectOneNs -XmlObject $Paragraph -XPath "./w:r/w:rPr"
    if ($null -eq $node) { $null } else { $node.CloneNode($true) }
}

function SnapshotParagraph([System.Xml.XmlNode]$Paragraph) {
    $ppr = $null
    $content = New-Object System.Collections.Generic.List[System.Xml.XmlNode]
    foreach ($child in @($Paragraph.ChildNodes)) {
        if ($child.LocalName -eq "pPr" -and $child.NamespaceURI -eq $script:W) { $ppr = $child.CloneNode($true) } else { $content.Add($child.CloneNode($true)) }
        [void]$Paragraph.RemoveChild($child)
    }
    [pscustomobject]@{ PPr = $ppr; Content = $content.ToArray() }
}

function AddRunText([System.Xml.XmlElement]$Run, [string]$Text, [bool]$Deleted) {
    $doc = $Run.OwnerDocument
    $tag = if ($Deleted) { "delText" } else { "t" }
    $buffer = New-Object System.Text.StringBuilder
    $flush = {
        if ($buffer.Length -eq 0) { return }
        $node = WNode $doc $tag
        $value = $buffer.ToString()
        if ($value.StartsWith(" ") -or $value.EndsWith(" ") -or $value.Contains("  ")) {
            $space = $doc.CreateAttribute("xml", "space", $script:XML)
            $space.Value = "preserve"
            [void]$node.Attributes.Append($space)
        }
        $node.InnerText = $value
        [void]$Run.AppendChild($node)
        [void]$buffer.Clear()
    }
    foreach ($char in ([string]$Text).ToCharArray()) {
        if ($char -eq "`n") { & $flush; [void]$Run.AppendChild((WNode $doc "br")) }
        elseif ($char -eq "`t") { & $flush; [void]$Run.AppendChild((WNode $doc "tab")) }
        else { [void]$buffer.Append([string]$char) }
    }
    & $flush
    if ($Run.ChildNodes.Count -eq 0) { $empty = WNode $doc $tag; $empty.InnerText = ""; [void]$Run.AppendChild($empty) }
}

function AppendRun([System.Xml.XmlNode]$Parent, [string]$Text, $RunProps, [bool]$Deleted = $false) {
    $doc = $Parent.OwnerDocument
    $run = WNode $doc "r"
    if ($null -ne $RunProps) { [void]$run.AppendChild($doc.ImportNode($RunProps, $true)) }
    AddRunText -Run $run -Text $Text -Deleted $Deleted
    [void]$Parent.AppendChild($run)
}

function RevNode([System.Xml.XmlDocument]$Doc, [string]$Name, [string]$Text, [int]$Id, [string]$AuthorText, [string]$DateText, $RunProps) {
    $node = WNode $Doc $Name
    SetWAttr $node "id" "$Id"
    SetWAttr $node "author" $AuthorText
    SetWAttr $node "date" $DateText
    AppendRun -Parent $node -Text $Text -RunProps $RunProps -Deleted ($Name -eq "del")
    $node
}

function NewDiffSegment([string]$Kind, [string]$Text) {
    [pscustomobject]@{ Kind = $Kind; Text = $Text }
}

function MergeDiffSegments($Segments) {
    $merged = @()
    foreach ($segment in $Segments) {
        if ($null -eq $segment -or [string]::IsNullOrEmpty([string]$segment.Text)) { continue }
        if ($merged.Count -gt 0) {
            $lastIndex = $merged.Count - 1
            $last = $merged[$lastIndex]
        } else {
            $lastIndex = -1
            $last = $null
        }
        if ($lastIndex -ge 0 -and $last.Kind -eq $segment.Kind) {
            $merged[$lastIndex] = (NewDiffSegment $last.Kind ([string]$last.Text + [string]$segment.Text))
        } else {
            $merged += ,(NewDiffSegment $segment.Kind ([string]$segment.Text))
        }
    }
    return $merged
}

function IsMergeableEqualSegment([string]$Text) {
    if ([string]::IsNullOrEmpty($Text) -or $Text -match '\s') { return $false }
    if ($Text -cmatch '^[\p{IsCJKUnifiedIdeographs}]{1,2}$') { return $true }
    if ($Text -cmatch '^[A-Za-z0-9]{1,4}$') { return $true }
    $false
}

function CollapseDiffWindow($WindowSegments) {
    $segments = @($WindowSegments)
    if ($segments.Count -eq 0) { return @() }
    $changeCount = @($segments | Where-Object { $_.Kind -ne "equal" }).Count
    $hasEqual = @($segments | Where-Object { $_.Kind -eq "equal" }).Count -gt 0
    if ($changeCount -le 1 -and -not $hasEqual) { return $segments }
    $oldText = ((@($segments | Where-Object { $_.Kind -in @("equal", "del") } | ForEach-Object { [string]$_.Text })) -join "")
    $newText = ((@($segments | Where-Object { $_.Kind -in @("equal", "ins") } | ForEach-Object { [string]$_.Text })) -join "")
    $collapsed = @()
    if (-not [string]::IsNullOrEmpty($oldText)) { $collapsed += ,(NewDiffSegment "del" $oldText) }
    if (-not [string]::IsNullOrEmpty($newText)) { $collapsed += ,(NewDiffSegment "ins" $newText) }
    return $collapsed
}

function CoalesceChangeWindows($Segments) {
    $segments = @($Segments)
    if ($segments.Count -eq 0) { return @() }
    $coalesced = @()
    $window = @()
    for ($i = 0; $i -lt $segments.Count; $i++) {
        $segment = $segments[$i]
        $prevKind = if ($i -gt 0) { [string]$segments[$i - 1].Kind } else { $null }
        $nextKind = if ($i + 1 -lt $segments.Count) { [string]$segments[$i + 1].Kind } else { $null }
        $isConnector = (
            $segment.Kind -eq "equal" -and
            $null -ne $prevKind -and
            $null -ne $nextKind -and
            $prevKind -ne "equal" -and
            $nextKind -ne "equal" -and
            (IsMergeableEqualSegment ([string]$segment.Text))
        )
        if ($segment.Kind -ne "equal" -or $isConnector) {
            $window += ,$segment
            continue
        }
        if ($window.Count -gt 0) {
            $coalesced += @(CollapseDiffWindow $window)
            $window = @()
        }
        $coalesced += ,$segment
    }
    if ($window.Count -gt 0) {
        $coalesced += @(CollapseDiffWindow $window)
    }
    return (MergeDiffSegments $coalesced)
}

function TokenizeDiffText([AllowNull()][string]$Text) {
    if ([string]::IsNullOrEmpty($Text)) { return @() }
    $pattern = "[0-9]+(?:[.,][0-9]+)*|[A-Za-z]+(?:[-_'][A-Za-z]+)*|[\p{IsCJKUnifiedIdeographs}]|[^\S\r\n]+|\r\n|\n|\r|."
    $tokens = New-Object System.Collections.Generic.List[string]
    foreach ($match in [System.Text.RegularExpressions.Regex]::Matches($Text, $pattern)) { $tokens.Add($match.Value) }
    return ,($tokens.ToArray())
}

function SliceTokenText($Tokens, [int]$Start, [int]$Count) {
    if ($Count -le 0) { return "" }
    if ($Count -eq 1) { return [string]$Tokens[$Start] }
    $end = $Start + $Count - 1
    (@($Tokens[$Start..$end]) -join "")
}

function CommonPrefixCount($LeftTokens, $RightTokens) {
    $left = @($LeftTokens)
    $right = @($RightTokens)
    $max = [Math]::Min($left.Count, $right.Count)
    $count = 0
    while ($count -lt $max -and $left[$count] -ceq $right[$count]) { $count++ }
    $count
}

function CommonSuffixCount($LeftTokens, $RightTokens, [int]$PrefixCount) {
    $left = @($LeftTokens)
    $right = @($RightTokens)
    $leftRemain = $left.Count - $PrefixCount
    $rightRemain = $right.Count - $PrefixCount
    $max = [Math]::Min($leftRemain, $rightRemain)
    $count = 0
    while ($count -lt $max -and $left[($left.Count - 1 - $count)] -ceq $right[($right.Count - 1 - $count)]) { $count++ }
    $count
}

function GetFallbackDiffSegments($OldTokens, $NewTokens) {
    $left = @($OldTokens)
    $right = @($NewTokens)
    $segments = New-Object System.Collections.Generic.List[object]
    $prefixCount = CommonPrefixCount $left $right
    $suffixCount = CommonSuffixCount $left $right $prefixCount
    $oldMiddleCount = $left.Count - $prefixCount - $suffixCount
    $newMiddleCount = $right.Count - $prefixCount - $suffixCount
    if ($prefixCount -gt 0) { $segments.Add((NewDiffSegment "equal" (SliceTokenText $left 0 $prefixCount))) }
    if ($oldMiddleCount -gt 0) { $segments.Add((NewDiffSegment "del" (SliceTokenText $left $prefixCount $oldMiddleCount))) }
    if ($newMiddleCount -gt 0) { $segments.Add((NewDiffSegment "ins" (SliceTokenText $right $prefixCount $newMiddleCount))) }
    if ($suffixCount -gt 0) { $segments.Add((NewDiffSegment "equal" (SliceTokenText $left ($left.Count - $suffixCount) $suffixCount))) }
    return (MergeDiffSegments $segments)
}

function GetMidDiffSegments($OldTokens, $NewTokens) {
    $left = @($OldTokens)
    $right = @($NewTokens)
    if ($left.Count -eq 0 -and $right.Count -eq 0) { return @() }
    if ($left.Count -eq 0) { return (NewDiffSegment "ins" ((@($right) -join ""))) }
    if ($right.Count -eq 0) { return (NewDiffSegment "del" ((@($left) -join ""))) }

    $cellLimit = 4000000
    $cells = [int64]($left.Count + 1) * [int64]($right.Count + 1)
    if ($cells -gt $cellLimit) { return (GetFallbackDiffSegments $left $right) }

    $dp = New-Object 'int[,]' ($left.Count + 1), ($right.Count + 1)
    for ($i = 0; $i -le $left.Count; $i++) { $dp[$i, 0] = $i }
    for ($j = 0; $j -le $right.Count; $j++) { $dp[0, $j] = $j }

    for ($i = 1; $i -le $left.Count; $i++) {
        for ($j = 1; $j -le $right.Count; $j++) {
            if ($left[($i - 1)] -ceq $right[($j - 1)]) {
                $dp[$i, $j] = $dp[($i - 1), ($j - 1)]
            } else {
                $deleteCost = $dp[($i - 1), $j] + 1
                $insertCost = $dp[$i, ($j - 1)] + 1
                $replaceCost = $dp[($i - 1), ($j - 1)] + 2
                $dp[$i, $j] = [Math]::Min($replaceCost, [Math]::Min($deleteCost, $insertCost))
            }
        }
    }

    $units = New-Object System.Collections.Generic.List[object]
    $i = $left.Count
    $j = $right.Count
    while ($i -gt 0 -or $j -gt 0) {
        if ($i -gt 0 -and $j -gt 0 -and $left[($i - 1)] -ceq $right[($j - 1)] -and $dp[$i, $j] -eq $dp[($i - 1), ($j - 1)]) {
            $units.Add((NewDiffSegment "equal" ([string]$left[($i - 1)])))
            $i--
            $j--
        } elseif ($i -gt 0 -and $dp[$i, $j] -eq ($dp[($i - 1), $j] + 1)) {
            $units.Add((NewDiffSegment "del" ([string]$left[($i - 1)])))
            $i--
        } elseif ($j -gt 0 -and $dp[$i, $j] -eq ($dp[$i, ($j - 1)] + 1)) {
            $units.Add((NewDiffSegment "ins" ([string]$right[($j - 1)])))
            $j--
        } else {
            if ($j -gt 0) { $units.Add((NewDiffSegment "ins" ([string]$right[($j - 1)]))); $j-- }
            if ($i -gt 0) { $units.Add((NewDiffSegment "del" ([string]$left[($i - 1)]))); $i-- }
        }
    }

    $ordered = $units.ToArray()
    [array]::Reverse($ordered)
    return (MergeDiffSegments $ordered)
}

function GetMinimalDiffSegments([AllowNull()][string]$OldText, [AllowNull()][string]$NewText) {
    $left = if ($null -eq $OldText) { "" } else { [string]$OldText }
    $right = if ($null -eq $NewText) { "" } else { [string]$NewText }
    $leftTokens = @(TokenizeDiffText $left)
    $rightTokens = @(TokenizeDiffText $right)
    $prefixCount = CommonPrefixCount $leftTokens $rightTokens
    $suffixCount = CommonSuffixCount $leftTokens $rightTokens $prefixCount
    $segments = New-Object System.Collections.Generic.List[object]
    $leftMiddleCount = $leftTokens.Count - $prefixCount - $suffixCount
    $rightMiddleCount = $rightTokens.Count - $prefixCount - $suffixCount
    if ($prefixCount -gt 0) { $segments.Add((NewDiffSegment "equal" (SliceTokenText $leftTokens 0 $prefixCount))) }
    if ($leftMiddleCount -gt 0 -or $rightMiddleCount -gt 0) {
        $leftMiddle = if ($leftMiddleCount -gt 0) { @($leftTokens[$prefixCount..($prefixCount + $leftMiddleCount - 1)]) } else { @() }
        $rightMiddle = if ($rightMiddleCount -gt 0) { @($rightTokens[$prefixCount..($prefixCount + $rightMiddleCount - 1)]) } else { @() }
        foreach ($segment in @(GetMidDiffSegments $leftMiddle $rightMiddle)) { $segments.Add($segment) }
    }
    if ($suffixCount -gt 0) { $segments.Add((NewDiffSegment "equal" (SliceTokenText $leftTokens ($leftTokens.Count - $suffixCount) $suffixCount))) }
    return (CoalesceChangeWindows (MergeDiffSegments $segments))
}

function WriteRevisionSegments([System.Xml.XmlNode]$Paragraph, $Segments, [ref]$NextRevision, [string]$AuthorText, [string]$DateText, $RunProps) {
    $changed = $false
    foreach ($segment in @($Segments)) {
        if ($null -eq $segment -or [string]::IsNullOrEmpty([string]$segment.Text)) { continue }
        switch ($segment.Kind) {
            "equal" {
                AppendRun -Parent $Paragraph -Text ([string]$segment.Text) -RunProps $RunProps -Deleted $false
            }
            "del" {
                [void]$Paragraph.AppendChild((RevNode $Paragraph.OwnerDocument "del" ([string]$segment.Text) $NextRevision.Value $AuthorText $DateText $RunProps))
                $NextRevision.Value++
                $changed = $true
            }
            "ins" {
                [void]$Paragraph.AppendChild((RevNode $Paragraph.OwnerDocument "ins" ([string]$segment.Text) $NextRevision.Value $AuthorText $DateText $RunProps))
                $NextRevision.Value++
                $changed = $true
            }
            default {
                throw "不支持的 diff 片段类型: $($segment.Kind)"
            }
        }
    }
    $changed
}

function ParagraphText([System.Xml.XmlNode]$Paragraph) {
    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($node in (SelectNodesNs -XmlObject $Paragraph -XPath ".//w:t | .//w:delText | .//w:instrText | .//w:tab | .//w:br | .//w:cr")) {
        switch ($node.LocalName) {
            "t" { $parts.Add($node.InnerText) }
            "delText" { $parts.Add($node.InnerText) }
            "instrText" { $parts.Add($node.InnerText) }
            "tab" { $parts.Add("`t") }
            default { $parts.Add("`n") }
        }
    }
    $parts -join ""
}

function ParagraphRefs([System.Xml.XmlDocument]$Doc) {
    $refs = New-Object System.Collections.Generic.List[object]
    foreach ($p in (SelectNodesNs -XmlObject $Doc -XPath "//w:p")) {
        $text = ParagraphText $p
        $refs.Add([pscustomobject]@{ Node = $p; Text = $text; Normalized = (Norm $text) })
    }
    return ,($refs.ToArray())
}

function ResolveParagraphTargetIndex($Paragraphs, $Location) {
    $Paragraphs = @($Paragraphs)
    if ($null -eq $Location) { return $null }
    $hasParagraphIndex = $null -ne $Location.PSObject.Properties["paragraph_index"]
    $hasParagraph = $null -ne $Location.PSObject.Properties["paragraph"]
    if (-not $hasParagraphIndex -and -not $hasParagraph) { throw "location 缺少 paragraph 或 paragraph_index" }

    if ($hasParagraphIndex) {
        $index = [int]$Location.paragraph_index
    } else {
        $paragraphNumber = [int]$Location.paragraph
        if ($paragraphNumber -le 0) { throw "location.paragraph 必须为正整数: $paragraphNumber" }
        $index = $paragraphNumber - 1
    }

    if ($index -lt 0 -or $index -ge $Paragraphs.Count) { throw "段落索引超出范围: $index" }
    return $index
}

function FindTargets($Paragraphs, $Operations) {
    $Paragraphs = @($Paragraphs)
    $Operations = @($Operations)
    $targets = New-Object System.Collections.Generic.List[object]
    $used = New-Object System.Collections.Generic.HashSet[int]
    foreach ($op in $Operations) {
        $idx = ResolveParagraphTargetIndex -Paragraphs $Paragraphs -Location $op.Location
        if ($null -eq $idx) {
            $matched = New-Object System.Collections.Generic.List[int]
            for ($i = 0; $i -lt $Paragraphs.Count; $i++) {
                $ok = if ($op.MatchType -eq "contains") { $Paragraphs[$i].Normalized.Contains((Norm $op.AnchorText)) } else { $Paragraphs[$i].Normalized -eq (Norm $op.AnchorText) }
                if ($ok) { $matched.Add($i) }
            }
            if ($matched.Count -lt $op.Occurrence) { throw "未找到第 $($op.Occurrence) 个匹配段落: $($op.AnchorText)" }
            $idx = $matched[$op.Occurrence - 1]
        }
        if (-not $used.Add($idx)) {
            $label = if ($null -ne $op.Location) { "段落索引 $idx" } else { [string]$op.AnchorText }
            throw "同一段落被重复命中: $label"
        }
        $targets.Add($Paragraphs[$idx])
    }
    return ,($targets.ToArray())
}

function AddCommentNode([System.Xml.XmlDocument]$Doc, [int]$Id, [string]$AuthorText, [string]$DateText, [string[]]$Lines) {
    $comment = WNode $Doc "comment"
    SetWAttr $comment "id" "$Id"
    SetWAttr $comment "author" $AuthorText
    SetWAttr $comment "date" $DateText
    foreach ($line in $Lines) {
        $p = WNode $Doc "p"
        $r = WNode $Doc "r"
        $rPr = WNode $Doc "rPr"
        $style = WNode $Doc "rStyle"
        SetWAttr $style "val" "CommentText"
        [void]$rPr.AppendChild($style)
        AddCommentFontProps -RunProps $rPr
        [void]$r.AppendChild($rPr)
        AddRunText -Run $r -Text $line -Deleted $false
        [void]$p.AppendChild($r)
        [void]$comment.AppendChild($p)
    }
    [void]$Doc.DocumentElement.AppendChild($comment)
}

function CRStart([System.Xml.XmlDocument]$Doc, [int]$Id) { $n = WNode $Doc "commentRangeStart"; SetWAttr $n "id" "$Id"; $n }
function CREnd([System.Xml.XmlDocument]$Doc, [int]$Id) { $n = WNode $Doc "commentRangeEnd"; SetWAttr $n "id" "$Id"; $n }
function CRefRun([System.Xml.XmlDocument]$Doc, [int]$Id) {
    $r = WNode $Doc "r"; $rPr = WNode $Doc "rPr"; $style = WNode $Doc "rStyle"; SetWAttr $style "val" "CommentReference"; [void]$rPr.AppendChild($style); [void]$r.AppendChild($rPr)
    $ref = WNode $Doc "commentReference"; SetWAttr $ref "id" "$Id"; [void]$r.AppendChild($ref); $r
}

function EnsureRelationship([System.Xml.XmlDocument]$Doc, [string]$Type, [string]$Target) {
    if ($null -ne (SelectOneNs -XmlObject $Doc -XPath "/pr:Relationships/pr:Relationship[@Type='$Type' and @Target='$Target']")) { return }
    $ids = @()
    foreach ($rel in (SelectNodesNs -XmlObject $Doc -XPath "/pr:Relationships/pr:Relationship")) { $ids += ([string]$rel.Attributes["Id"].Value).Replace("rId", "") }
    $node = $Doc.CreateElement("Relationship", $script:PR)
    [void]$node.SetAttribute("Id", "rId$(NextId $ids)")
    [void]$node.SetAttribute("Type", $Type)
    [void]$node.SetAttribute("Target", $Target)
    [void]$Doc.DocumentElement.AppendChild($node)
}

function EnsureOverride([System.Xml.XmlDocument]$Doc, [string]$PartName, [string]$ContentType) {
    $existing = SelectOneNs -XmlObject $Doc -XPath "/ct:Types/ct:Override[@PartName='$PartName']"
    if ($null -ne $existing) { [void]$existing.SetAttribute("ContentType", $ContentType); return }
    $node = $Doc.CreateElement("Override", $script:CT)
    [void]$node.SetAttribute("PartName", $PartName)
    [void]$node.SetAttribute("ContentType", $ContentType)
    [void]$Doc.DocumentElement.AppendChild($node)
}

function EnsureComments([string]$Workspace) {
    $commentsPath = Join-Path $Workspace "word\comments.xml"
    $relsPath = Join-Path $Workspace "word\_rels\document.xml.rels"
    $typesPath = Join-Path $Workspace "[Content_Types].xml"
    $doc = if (Test-Path $commentsPath) { LoadXml $commentsPath } else { NewDoc "comments" $script:W "w" }
    [System.IO.Directory]::CreateDirectory((Split-Path -Parent $relsPath)) | Out-Null
    $rels = if (Test-Path $relsPath) { LoadXml $relsPath } else { NewDoc "Relationships" $script:PR "" }
    EnsureRelationship $rels $script:CommentsRel "comments.xml"
    SaveXml $rels $relsPath
    $types = LoadXml $typesPath
    EnsureOverride $types "/word/comments.xml" $script:CommentsType
    SaveXml $types $typesPath
    SaveXml $doc $commentsPath
    $doc
}

function EnsureSettings([string]$Workspace) {
    $settingsPath = Join-Path $Workspace "word\settings.xml"
    $relsPath = Join-Path $Workspace "word\_rels\document.xml.rels"
    $typesPath = Join-Path $Workspace "[Content_Types].xml"
    $doc = if (Test-Path $settingsPath) { LoadXml $settingsPath } else { NewDoc "settings" $script:W "w" }
    if ($null -eq (SelectOneNs -XmlObject $doc -XPath "/w:settings/w:trackRevisions")) { [void]$doc.DocumentElement.AppendChild((WNode $doc "trackRevisions")) }
    if ($null -eq (SelectOneNs -XmlObject $doc -XPath "/w:settings/w:showRevisions")) { [void]$doc.DocumentElement.AppendChild((WNode $doc "showRevisions")) }
    [System.IO.Directory]::CreateDirectory((Split-Path -Parent $relsPath)) | Out-Null
    $rels = if (Test-Path $relsPath) { LoadXml $relsPath } else { NewDoc "Relationships" $script:PR "" }
    EnsureRelationship $rels $script:SettingsRel "settings.xml"
    SaveXml $rels $relsPath
    $types = LoadXml $typesPath
    EnsureOverride $types "/word/settings.xml" $script:SettingsType
    SaveXml $types $typesPath
    SaveXml $doc $settingsPath
}

function CurrentCommentId([System.Xml.XmlDocument]$Doc) {
    $ids = @()
    foreach ($node in (SelectNodesNs -XmlObject $Doc -XPath "/w:comments/w:comment")) { $ids += [string]$node.Attributes.GetNamedItem("id", $script:W).Value }
    NextId $ids
}

function CurrentRevisionId([System.Xml.XmlDocument]$Doc) {
    $ids = @()
    foreach ($path in @("//w:ins", "//w:del")) {
        foreach ($node in (SelectNodesNs -XmlObject $Doc -XPath $path)) {
            $attr = $node.Attributes.GetNamedItem("id", $script:W)
            if ($null -ne $attr) { $ids += [string]$attr.Value }
        }
    }
    NextId $ids
}

function Reset-Workspace([string]$Workspace) {
    if (Test-Path -LiteralPath $Workspace) { Remove-Item -LiteralPath $Workspace -Recurse -Force }
    [System.IO.Directory]::CreateDirectory($Workspace) | Out-Null
}

function Supports-ShellZipFallback {
    if ($null -ne (Get-Variable -Name IsWindows -ErrorAction SilentlyContinue)) {
        return [bool]$IsWindows
    }
    [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)
}

function ExpandDocxWithDotNet([string]$Docx, [string]$Workspace) {
    Ensure-DotNetCompression
    [System.IO.Compression.ZipFile]::ExtractToDirectory($Docx, $Workspace)
}

function ExpandDocxWithShell([string]$Docx, [string]$Workspace) {
    $shell = New-Object -ComObject Shell.Application
    try {
        $sourceNs = $shell.NameSpace($Docx)
        $targetNs = $shell.NameSpace($Workspace)
        if ($null -eq $sourceNs -or $null -eq $targetNs) {
            throw "Shell ZIP 后端无法打开源或目标路径。"
        }
        $targetNs.CopyHere($sourceNs.Items(), 16)
        $deadline = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $deadline) {
            if (Test-Path (Join-Path $Workspace "word\document.xml")) { break }
            Start-Sleep -Milliseconds 200
        }
        if (-not (Test-Path (Join-Path $Workspace "word\document.xml"))) {
            throw "Shell ZIP 后端解压超时。"
        }
    }
    finally {
        if ($shell -is [System.__ComObject]) {
            [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($shell)
        }
    }
}

function ExpandDocx([string]$Docx, [string]$Workspace) {
    $dotNetError = $null
    Reset-Workspace $Workspace
    try {
        ExpandDocxWithDotNet $Docx $Workspace
        return
    }
    catch {
        $dotNetError = $_
    }

    if (-not (Supports-ShellZipFallback)) {
        throw "DOCX 解压失败。.NET ZipArchive: $($dotNetError.Exception.Message)。当前平台不支持 Shell.Application 回退，请在 macOS/Linux 上优先使用 pwsh + .NET ZipArchive。"
    }

    Reset-Workspace $Workspace
    try {
        ExpandDocxWithShell $Docx $Workspace
        return
    }
    catch {
        throw "DOCX 解压失败。.NET ZipArchive: $($dotNetError.Exception.Message)；Shell.Application: $($_.Exception.Message)"
    }
}

function PackDocxWithDotNet([string]$Workspace, [string]$Docx) {
    Ensure-DotNetCompression
    $workspaceRoot = [System.IO.Path]::GetFullPath($Workspace)
    if (-not $workspaceRoot.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $workspaceRoot += [System.IO.Path]::DirectorySeparatorChar
    }
    $stream = [System.IO.File]::Open($Docx, [System.IO.FileMode]::Create)
    try {
        $zip = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
        try {
            Get-ChildItem -LiteralPath $Workspace -Recurse -File | Sort-Object FullName | ForEach-Object {
                $rel = $_.FullName.Substring($workspaceRoot.Length).Replace("\", "/")
                $entry = $zip.CreateEntry($rel, [System.IO.Compression.CompressionLevel]::Optimal)
                $target = $entry.Open()
                try { $file = [System.IO.File]::OpenRead($_.FullName); try { $file.CopyTo($target) } finally { $file.Dispose() } } finally { $target.Dispose() }
            }
        } finally { $zip.Dispose() }
    } finally { $stream.Dispose() }
}

function PackDocxWithShell([string]$Workspace, [string]$Docx) {
    [System.IO.File]::WriteAllBytes($Docx, [byte[]](80,75,5,6,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0))
    $shell = New-Object -ComObject Shell.Application
    try {
        $zipNs = $shell.NameSpace($Docx)
        $srcNs = $shell.NameSpace($Workspace)
        if ($null -eq $zipNs -or $null -eq $srcNs) {
            throw "Shell ZIP 后端无法创建 ZIP 容器。"
        }
        $zipNs.CopyHere($srcNs.Items(), 16)
        $deadline = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $deadline) {
            $probe = $shell.NameSpace($Docx)
            if ($null -ne $probe -and $null -ne $probe.ParseName("[Content_Types].xml") -and $null -ne $probe.ParseName("word")) {
                break
            }
            Start-Sleep -Milliseconds 250
        }
    }
    finally {
        if ($shell -is [System.__ComObject]) {
            [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($shell)
        }
    }
}

function PackDocx([string]$Workspace, [string]$Docx) {
    if (Test-Path $Docx) { Remove-Item -LiteralPath $Docx -Force }
    $parent = Split-Path -Parent $Docx
    if ($parent) { [System.IO.Directory]::CreateDirectory($parent) | Out-Null }
    $dotNetError = $null
    try {
        PackDocxWithDotNet $Workspace $Docx
        return
    }
    catch {
        $dotNetError = $_
    }

    if (-not (Supports-ShellZipFallback)) {
        throw "DOCX 回包失败。.NET ZipArchive: $($dotNetError.Exception.Message)。当前平台不支持 Shell.Application 回退，请在 macOS/Linux 上优先使用 pwsh + .NET ZipArchive。"
    }

    if (Test-Path -LiteralPath $Docx) { Remove-Item -LiteralPath $Docx -Force }
    try {
        PackDocxWithShell $Workspace $Docx
        return
    }
    catch {
        throw "DOCX 回包失败。.NET ZipArchive: $($dotNetError.Exception.Message)；Shell.Application: $($_.Exception.Message)"
    }
}

function ApplyReviewed([string]$Workspace, [object[]]$Operations, [string]$AuthorText, [string]$DateText) {
    $documentPath = Join-Path $Workspace "word\document.xml"
    $doc = LoadXml $documentPath
    $paragraphs = ParagraphRefs $doc
    $targets = FindTargets -Paragraphs $paragraphs -Operations $Operations
    $commentsDoc = $null
    $nextComment = 0
    if (@($Operations | Where-Object { $_.Mode -in @("comment", "revision_comment") }).Count -gt 0) { $commentsDoc = EnsureComments $Workspace; $nextComment = CurrentCommentId $commentsDoc }
    if (@($Operations | Where-Object { $_.Mode -in @("revision", "revision_comment") }).Count -gt 0) { EnsureSettings $Workspace }
    $nextRevision = CurrentRevisionId $doc
    $commentCount = 0
    $revisionCount = 0
    for ($i = 0; $i -lt $Operations.Count; $i++) {
        $op = $Operations[$i]
        $target = $targets[$i]
        $p = $target.Node
        $runProps = RunPropsClone $p
        $snapshot = SnapshotParagraph $p
        if ($null -ne $snapshot.PPr) { [void]$p.AppendChild($p.OwnerDocument.ImportNode($snapshot.PPr, $true)) }
        $commentId = $null
        if ($op.Mode -in @("comment", "revision_comment")) {
            $commentId = $nextComment; $nextComment++
            [void]$p.AppendChild((CRStart $p.OwnerDocument $commentId))
            AddCommentNode -Doc $commentsDoc -Id $commentId -AuthorText $AuthorText -DateText $DateText -Lines $op.CommentLines
            $commentCount++
        }
        if ($op.Mode -eq "comment") {
            if ($snapshot.Content.Count -gt 0) { foreach ($node in $snapshot.Content) { [void]$p.AppendChild($p.OwnerDocument.ImportNode($node, $true)) } } else { AppendRun $p $target.Text $runProps $false }
        } else {
            $segments = GetMinimalDiffSegments $target.Text ([string]$op.ReplacementText)
            $changed = WriteRevisionSegments -Paragraph $p -Segments $segments -NextRevision ([ref]$nextRevision) -AuthorText $AuthorText -DateText $DateText -RunProps $runProps
            if (-not $changed) { AppendRun $p $target.Text $runProps $false } else { $revisionCount++ }
        }
        if ($null -ne $commentId) { [void]$p.AppendChild((CREnd $p.OwnerDocument $commentId)); [void]$p.AppendChild((CRefRun $p.OwnerDocument $commentId)) }
    }
    SaveXml $doc $documentPath
    if ($null -ne $commentsDoc) { SaveXml $commentsDoc (Join-Path $Workspace "word\comments.xml") }
    [pscustomobject]@{ Comments = $commentCount; Revisions = $revisionCount }
}

function ReplaceParagraphText([System.Xml.XmlNode]$Paragraph, [string]$Text) {
    $runProps = RunPropsClone $Paragraph
    $snapshot = SnapshotParagraph $Paragraph
    if ($null -ne $snapshot.PPr) { [void]$Paragraph.AppendChild($Paragraph.OwnerDocument.ImportNode($snapshot.PPr, $true)) }
    AppendRun $Paragraph $Text $runProps $false
}

function ApplyClean([string]$Workspace, [object[]]$Operations) {
    $documentPath = Join-Path $Workspace "word\document.xml"
    $doc = LoadXml $documentPath
    $paragraphs = ParagraphRefs $doc
    $targets = FindTargets -Paragraphs $paragraphs -Operations $Operations
    $count = 0
    for ($i = 0; $i -lt $Operations.Count; $i++) { if ($Operations[$i].Mode -in @("revision", "revision_comment")) { ReplaceParagraphText $targets[$i].Node ([string]$Operations[$i].ReplacementText); $count++ } }
    SaveXml $doc $documentPath
    $count
}

function ValidateDocx([string]$Docx, [bool]$NeedComments, [bool]$NeedRevisions) {
    $workspace = Join-Path ([System.IO.Path]::GetTempPath()) ("review-validate-" + [guid]::NewGuid().ToString("N"))
    try {
        ExpandDocx $Docx $workspace
        $docPath = Join-Path $workspace "word\document.xml"
        if (-not (Test-Path $docPath)) { throw "输出文件缺少 word/document.xml: $Docx" }
        $doc = LoadXml $docPath
        if ($NeedComments) {
            $commentsPath = Join-Path $workspace "word\comments.xml"
            if (-not (Test-Path $commentsPath)) { throw "输出文件缺少 word/comments.xml: $Docx" }
            if ($null -eq (SelectOneNs -XmlObject $doc -XPath "//w:commentRangeStart")) { throw "输出文件未写入批注标记: $Docx" }
            $comments = LoadXml $commentsPath
            if ($null -eq (SelectOneNs -XmlObject $comments -XPath "//w:comment//w:rPr/w:rFonts[@w:eastAsia='$($script:CommentFontName)']")) {
                throw "输出文件批注字体未锁定为宋体(SimSun): $Docx"
            }
        }
        if ($NeedRevisions) {
            $settingsPath = Join-Path $workspace "word\settings.xml"
            if (-not (Test-Path $settingsPath)) { throw "输出文件缺少 word/settings.xml: $Docx" }
            $settings = LoadXml $settingsPath
            if ($null -eq (SelectOneNs -XmlObject $settings -XPath "/w:settings/w:trackRevisions")) { throw "输出文件未开启修订模式: $Docx" }
            if ($null -eq (SelectOneNs -XmlObject $settings -XPath "/w:settings/w:showRevisions")) { throw "输出文件未开启修订显示: $Docx" }
            $hasInsertion = $null -ne (SelectOneNs -XmlObject $doc -XPath "//w:ins")
            $hasDeletion = $null -ne (SelectOneNs -XmlObject $doc -XPath "//w:del")
            if (-not $hasInsertion -and -not $hasDeletion) { throw "输出文件未写入修订痕迹: $Docx" }
        }
    } finally { if (Test-Path $workspace) { Remove-Item -LiteralPath $workspace -Recurse -Force } }
}

$sourcePath = FullPath $Source
$instructionsPath = FullPath $Instructions
$outputPath = FullPath $Output
$cleanOutputPath = if ([string]::IsNullOrWhiteSpace($CleanOutput)) { $null } else { FullPath $CleanOutput }

if (-not (Test-Path -LiteralPath $sourcePath)) { throw "源文件不存在: $sourcePath" }
if (-not (Test-Path -LiteralPath $instructionsPath)) { throw "指令文件不存在: $instructionsPath" }
if ([System.IO.Path]::GetExtension($sourcePath).ToLowerInvariant() -ne ".docx") { throw "source 必须是 .docx 文件" }
if ([System.IO.Path]::GetExtension($instructionsPath).ToLowerInvariant() -ne ".json") { throw "instructions 必须是 .json 文件" }

$useStaging = Use-Staging @($sourcePath, $instructionsPath, $outputPath, $cleanOutputPath)
$stagingInfo = $null
$processingSourcePath = $sourcePath
$processingInstructionsPath = $instructionsPath
$processingOutputPath = $outputPath
$processingCleanOutputPath = $cleanOutputPath

if ($useStaging) {
    $stagingInfo = Invoke-Staging -SourcePath $sourcePath -InstructionsPath $instructionsPath
    $processingSourcePath = FullPath ([string]$stagingInfo.staged_source)
    $processingInstructionsPath = FullPath ([string]$stagingInfo.staged_instructions)
    $processingOutputPath = FullPath ([string]$stagingInfo.staged_reviewed_docx)
    if ($cleanOutputPath) {
        $processingCleanOutputPath = FullPath ([string]$stagingInfo.staged_clean_docx)
    } else {
        $processingCleanOutputPath = $null
    }
}

$summary = $null
try {
    $config = Read-JsonFile $processingInstructionsPath
    $effectiveAuthor = if ($null -ne $config.PSObject.Properties["author"] -and -not [string]::IsNullOrWhiteSpace([string]$config.author)) { [string]$config.author } else { $Author }
    $effectiveDate = Iso ($(if ($null -ne $config.PSObject.Properties["date"]) { [string]$config.date } else { $Date }))
    $operations = @()
    foreach ($raw in @($config.operations)) {
        $comment = if ($null -ne $raw.PSObject.Properties["comment"]) {
            if ($raw.comment -is [string]) { [ordered]@{ "问题" = [string]$raw.comment } } else {
                $h = [ordered]@{}
                foreach ($key in @("问题", "风险", "修改建议", "建议条款", "修改依据")) {
                    $prop = $raw.comment.PSObject.Properties[$key]
                    if ($null -ne $prop -and -not [string]::IsNullOrWhiteSpace([string]$prop.Value)) {
                        $h[$key] = [string]$prop.Value
                    }
                }
                if ($h.Count -eq 0) { $null } else { $h }
            }
        } else { $null }
        $commentLines = @()
        if ($null -ne $comment) {
            foreach ($key in @("问题", "风险", "修改建议", "建议条款", "修改依据")) {
                if ($comment.Contains($key) -and -not [string]::IsNullOrWhiteSpace([string]$comment[$key])) {
                    $commentLines += "${key}：$($comment[$key])"
                }
            }
        }
        if ($commentLines.Count -eq 0) { $commentLines = @("问题：未提供批注内容") }
        $mode = [string]$raw.mode; if ([string]::IsNullOrWhiteSpace($mode)) { $mode = $DefaultMode }; $mode = $mode.ToLowerInvariant()
        if ($mode -notin @("comment", "revision", "revision_comment")) { throw "operation mode 不合法: $mode" }
        $occurrence = if ($null -ne $raw.PSObject.Properties["occurrence"]) { [int]$raw.occurrence } else { 1 }
        $matchType = if ($null -ne $raw.PSObject.Properties["match_type"] -and -not [string]::IsNullOrWhiteSpace([string]$raw.match_type)) { ([string]$raw.match_type).ToLowerInvariant() } else { "exact" }
        $location = if ($null -ne $raw.PSObject.Properties["location"]) { $raw.location } else { $null }
        $anchorText = if ($null -ne $raw.PSObject.Properties["anchor_text"]) { [string]$raw.anchor_text } else { $null }
        if ($null -eq $location -and [string]::IsNullOrWhiteSpace($anchorText)) { throw "operation 缺少 anchor_text 或 location" }
        if ($mode -in @("revision", "revision_comment") -and $null -eq $raw.PSObject.Properties["replacement_text"]) { throw "修订 operation 缺少 replacement_text" }
        if ($mode -in @("comment", "revision_comment") -and $null -eq $comment) { throw "批注 operation 缺少 comment" }
        $operations += [pscustomobject]@{
            AnchorText = $anchorText
            Location = $location
            Mode = $mode
            ReplacementText = $(if ($null -ne $raw.PSObject.Properties["replacement_text"]) { [string]$raw.replacement_text } else { $null })
            Comment = $comment
            CommentLines = $commentLines
            MatchType = $matchType
            Occurrence = $occurrence
        }
    }
    if ($operations.Count -eq 0) { throw "instructions.json 必须包含非空 operations 数组" }

    CopyDocx $processingSourcePath $processingOutputPath
    $reviewWorkspace = Join-Path ([System.IO.Path]::GetTempPath()) ("review-docx-" + [guid]::NewGuid().ToString("N"))
    try { ExpandDocx $processingOutputPath $reviewWorkspace; $review = ApplyReviewed $reviewWorkspace $operations $effectiveAuthor $effectiveDate; PackDocx $reviewWorkspace $processingOutputPath } finally { if (Test-Path $reviewWorkspace) { Remove-Item -LiteralPath $reviewWorkspace -Recurse -Force } }
    $needComments = @($operations | Where-Object { $_.Mode -in @("comment", "revision_comment") }).Count -gt 0
    $needRevisions = @($operations | Where-Object { $_.Mode -in @("revision", "revision_comment") }).Count -gt 0
    ValidateDocx $processingOutputPath $needComments $needRevisions

    if ($useStaging) { CopyDocx $processingOutputPath $outputPath }

    $summary = [ordered]@{
        source               = $sourcePath
        instructions         = $instructionsPath
        output               = $outputPath
        author               = $effectiveAuthor
        date                 = $effectiveDate
        operations_applied   = $operations.Count
        comments_applied     = $review.Comments
        revisions_applied    = $review.Revisions
        staging_applied      = $useStaging
        processing_source    = $processingSourcePath
        processing_instructions = $processingInstructionsPath
        processing_output    = $processingOutputPath
        review_comment_impl  = "direct_xml"
        xml_editing_locked   = $true
    }
    if ($useStaging) {
        $summary["staging_workspace"] = [string]$stagingInfo.workspace_root
        $summary["staging_reason"] = "non_ascii_path"
    }
    if ($cleanOutputPath) {
        CopyDocx $processingSourcePath $processingCleanOutputPath
        $cleanWorkspace = Join-Path ([System.IO.Path]::GetTempPath()) ("clean-docx-" + [guid]::NewGuid().ToString("N"))
        try { ExpandDocx $processingCleanOutputPath $cleanWorkspace; $cleanChanges = ApplyClean $cleanWorkspace $operations; PackDocx $cleanWorkspace $processingCleanOutputPath } finally { if (Test-Path $cleanWorkspace) { Remove-Item -LiteralPath $cleanWorkspace -Recurse -Force } }
        ValidateDocx $processingCleanOutputPath $false $false
        if ($useStaging) { CopyDocx $processingCleanOutputPath $cleanOutputPath }
        $summary["clean_output"] = $cleanOutputPath
        $summary["clean_changes"] = $cleanChanges
        $summary["processing_clean_output"] = $processingCleanOutputPath
    }

    $summary | ConvertTo-Json -Depth 6
}
finally {
    if ($useStaging -and $null -ne $stagingInfo -and -not [string]::IsNullOrWhiteSpace([string]$stagingInfo.workspace_root) -and (Test-Path -LiteralPath ([string]$stagingInfo.workspace_root))) {
        Remove-Item -LiteralPath ([string]$stagingInfo.workspace_root) -Recurse -Force
    }
}
