# Параметры скрипта
param(
    [string]$Branch = "main"
)

# ===== НАСТРОЙКИ GITHUB =====
# Целевой репозиторий для push/tags
$TARGET_GITHUB_REPO = "Popovich52/wozym"
$TARGET_GITHUB_REMOTE = "https://github.com/$TARGET_GITHUB_REPO.git"

# GitHub token берем только из переменной окружения, чтобы не хранить секрет в git.
# PowerShell (текущая сессия): $env:GITHUB_TOKEN = "your_token_here"
$GITHUB_TOKEN = $env:GITHUB_TOKEN

# Функция для работы с GitHub API
function Get-GitHubData {
    param(
        [string]$Token,
        [string]$Repo = $TARGET_GITHUB_REPO
    )
    
    if ([string]::IsNullOrWhiteSpace($Token)) {
        Write-Host "⚠️  GitHub токен не настроен!" -ForegroundColor Yellow
        Write-Host "   Установите переменную окружения GITHUB_TOKEN" -ForegroundColor Gray
        return @{ releases = $null; tags = $null }
    }
    
    try {
        $headers = @{
            "Authorization" = "Bearer $Token"
            "Accept"        = "application/vnd.github.v3+json"
            "User-Agent"    = "PowerShell-QuickCommit"
        }
        
        Write-Host "🔑 Использую GitHub API с токеном..." -ForegroundColor Cyan
        
        # Получаем релизы
        $releasesUrl = "https://api.github.com/repos/$Repo/releases?per_page=5"
        $releases = Invoke-RestMethod -Uri $releasesUrl -Headers $headers -TimeoutSec 15
        
        # Получаем теги
        $tagsUrl = "https://api.github.com/repos/$Repo/tags?per_page=10"
        $tagsData = Invoke-RestMethod -Uri $tagsUrl -Headers $headers -TimeoutSec 15
        $tags = $tagsData | ForEach-Object { $_.name }
        
        Write-Host "✅ Данные получены через GitHub API" -ForegroundColor Green
        return @{ 
            releases = $releases | Select-Object @{n = 'tagName'; e = { $_.tag_name } }, @{n = 'name'; e = { $_.name } }, @{n = 'publishedAt'; e = { $_.published_at } }
            tags     = $tags 
        }
    }
    catch {
        Write-Host "❌ Ошибка GitHub API: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Message -match "401|403") {
            Write-Host "   Проверьте правильность токена и его права (repo, workflow)" -ForegroundColor Gray
        }
        return @{ releases = $null; tags = $null }
    }
}

# Проверка: запуск из git-репозитория
if (-not (Test-Path ".git")) {
    Write-Error "Это не git-репозиторий. Перейдите в папку проекта."
    exit 1
}

# Настройки
$branchName = $Branch
$originUrl = git remote get-url origin 2>$null
if (-not $originUrl) {
    Write-Host "🔧 Настраиваю origin -> $TARGET_GITHUB_REMOTE" -ForegroundColor Cyan
    git remote add origin $TARGET_GITHUB_REMOTE
}

function Test-TagExists {
    param(
        [string]$TagName
    )
    $exact = git tag --list $TagName
    return -not [string]::IsNullOrWhiteSpace($exact)
}

function Get-NextAvailableVersion {
    param(
        [string]$Version
    )

    $parts = $Version -split '\.'
    if ($parts.Count -ne 3) {
        return $Version
    }

    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    $patch = [int]$parts[2]
    $candidate = "$major.$minor.$patch"

    while (Test-TagExists -TagName "v$candidate") {
        $patch++
        $candidate = "$major.$minor.$patch"
    }

    return $candidate
}
elseif ($originUrl -notmatch 'github\.com[:/]Popovich52/wozym(\.git)?$') {
    Write-Host "🔧 Обновляю origin -> $TARGET_GITHUB_REMOTE" -ForegroundColor Cyan
    git remote set-url origin $TARGET_GITHUB_REMOTE
}

Write-Host "🚀 Git Quick Commit Script" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

# Всегда запрашиваем комментарий от пользователя
$customComment = Read-Host "📝 Введите комментарий к коммиту"
if ([string]::IsNullOrWhiteSpace($customComment)) {
    $customComment = "Обновление логики API"
    Write-Host "ℹ️  Используется стандартный комментарий: $customComment" -ForegroundColor Yellow
}

# Получаем последний semver-тег из git
$latestTag = git tag --list "v*" --sort=-version:refname | Select-Object -First 1
if (-not $latestTag) {
    Write-Host "⚠️  Git теги не найдены. Устанавливаем начальную версию v1.0.0" -ForegroundColor Yellow
    $currentVersion = "1.0.0"
}
else {
    # Убираем префикс 'v' если есть
    $currentVersion = $latestTag -replace '^v', ''
    Write-Host "🔍 Найден последний тег: $latestTag" -ForegroundColor Cyan
}

# Разбиваем версию на части
$parts = $currentVersion -split '\.'

# Увеличиваем patch (x.y.z) для предложения по умолчанию
$parts[2] = [int]$parts[2] + 1
$suggestedVersion = "$($parts[0]).$($parts[1]).$($parts[2])"

Write-Host "📈 Предлагаемая следующая версия: v$suggestedVersion" -ForegroundColor Green

# Запрашиваем версию у пользователя
Write-Host ""
$userVersion = Read-Host "🏷️  Введите версию тега (Enter для v$suggestedVersion)"
if ([string]::IsNullOrWhiteSpace($userVersion)) {
    $newVersion = $suggestedVersion
    Write-Host "✅ Используется предлагаемая версия: v$newVersion" -ForegroundColor Green
}
else {
    # Убираем префикс 'v' если пользователь его ввёл
    $newVersion = $userVersion -replace '^v', ''
    Write-Host "✅ Используется пользовательская версия: v$newVersion" -ForegroundColor Green
}

$availableVersion = Get-NextAvailableVersion -Version $newVersion
if ($availableVersion -ne $newVersion) {
    Write-Host "⚠️  Тег v$newVersion уже существует. Переключаюсь на v$availableVersion." -ForegroundColor Yellow
    $newVersion = $availableVersion
}

# Сообщение коммита
$commitMessage = "$customComment | v$newVersion"

# Показываем предварительный просмотр
Write-Host ""
Write-Host "📋 ПРЕДВАРИТЕЛЬНЫЙ ПРОСМОТР:" -ForegroundColor Magenta
Write-Host "=================================" -ForegroundColor Magenta
Write-Host "Коммит сообщение: $commitMessage" -ForegroundColor White
Write-Host "Новый тег: v$newVersion" -ForegroundColor White
Write-Host "Ветка: $branchName" -ForegroundColor White
Write-Host "=================================" -ForegroundColor Magenta
Write-Host ""

# Запрашиваем подтверждение
$confirmation = Read-Host "✅ Продолжить отправку? (y/n, Enter = да)"
if ($confirmation -and $confirmation.ToLower() -notmatch '^(y|yes|д|да)$') {
    Write-Host "❌ Операция отменена пользователем" -ForegroundColor Red
    exit 0
}

# Git: add, commit, push
Write-Host ""
Write-Host "🔄 Выполняю Git операции..." -ForegroundColor Cyan

Write-Host "📊 Обновляю Graphify граф проекта..." -ForegroundColor Gray
npm run graphify
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Graphify не обновился. Продолжаю без остановки." -ForegroundColor Yellow
}

Write-Host "➕ Добавляю изменения в индекс..." -ForegroundColor Gray
git add .

Write-Host "💾 Создаю коммит..." -ForegroundColor Gray
git commit -m $commitMessage
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка создания коммита. Прерываю." -ForegroundColor Red
    exit 1
}

Write-Host "🏷️  Создаю тег v$newVersion..." -ForegroundColor Gray
git tag -a "v$newVersion" -m $commitMessage
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка создания тега. Прерываю." -ForegroundColor Red
    exit 1
}

Write-Host "🚀 Отправляю коммит в ветку $branchName..." -ForegroundColor Gray
git push origin $branchName
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Push ветки не выполнен. Прерываю." -ForegroundColor Red
    exit 1
}

Write-Host "🏷️  Отправляю тег v$newVersion на GitHub..." -ForegroundColor Gray
git push origin "v$newVersion"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Push тега не выполнен. Прерываю." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 УСПЕШНО ЗАВЕРШЕНО!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host "✅ Коммит отправлен: $commitMessage" -ForegroundColor White
Write-Host "✅ Тег создан: v$newVersion" -ForegroundColor White
Write-Host "✅ Всё отправлено на GitHub" -ForegroundColor White
Write-Host "=================================" -ForegroundColor Green

# Показываем последние версии
Write-Host ""
Write-Host "📋 ПОСЛЕДНИЕ ВЕРСИИ:" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Получаем последние 10 тегов, отсортированных по версии
Write-Host "🏷️  Последние теги в Git:" -ForegroundColor Yellow
$recentTags = git tag --sort=-version:refname | Select-Object -First 10
if ($recentTags) {
    foreach ($tag in $recentTags) {
        if ($tag -eq "v$newVersion") {
            Write-Host "  → $tag (НОВЫЙ)" -ForegroundColor Green
        }
        else {
            Write-Host "  → $tag" -ForegroundColor White
        }
    }
}
else {
    Write-Host "  Нет доступных тегов" -ForegroundColor Gray
}

Write-Host ""
Write-Host "🌐 ПРОВЕРКА GITHUB:" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Проверяем последние релизы на GitHub
Write-Host "📡 Проверяю последние релизы на GitHub..." -ForegroundColor Yellow
try {
    # Сначала проверяем настройки git remote
    $remoteUrl = git config --get remote.origin.url
    Write-Host "🔗 Remote URL: $remoteUrl" -ForegroundColor Gray
    
    # Проверяем подключение к GitHub
    Write-Host "🔄 Проверяю подключение к GitHub..." -ForegroundColor Gray
    $testConnection = git ls-remote --heads origin 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка подключения к GitHub:" -ForegroundColor Red
        Write-Host "   $testConnection" -ForegroundColor Red
        Write-Host "   Проверьте настройки в GITHUB_SETUP.md" -ForegroundColor Yellow
        throw "GitHub connection failed"
    }
    
    # Сначала пробуем через gh (если авторизован)
    $githubReleases = $null
    $githubTags = $null
    
    try {
        # Способ 1: Проверяем авторизацию GitHub CLI
        $ghAuth = gh auth status 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ GitHub CLI авторизован" -ForegroundColor Green
            $githubReleases = gh release list --limit 5 --json tagName, name, publishedAt 2>$null | ConvertFrom-Json
            $githubTags = gh api "repos/$TARGET_GITHUB_REPO/tags" --jq '.[0:10] | .[] | .name' 2>$null
        }
        else {
            Write-Host "⚠️  GitHub CLI не авторизован" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "ℹ️  GitHub CLI недоступен" -ForegroundColor Gray
    }

    # Способ 2: Если GitHub CLI не дал результаты, пробуем GitHub API с токеном
    if ((-not $githubReleases -or -not $githubTags)) {
        $githubData = Get-GitHubData -Token $GITHUB_TOKEN
        $githubReleases = $githubData.releases
        $githubTags = $githubData.tags
    }
    
    # Если gh не сработал, получаем теги через git
    if (-not $githubTags) {
        Write-Host "🔄 Получаю теги с GitHub через git..." -ForegroundColor Yellow
        git fetch --tags origin 2>$null
        $allRemoteTags = git ls-remote --tags origin 2>$null
        if ($allRemoteTags) {
            # Парсим теги из git ls-remote (убираем дубликаты и сортируем)
            $githubTags = $allRemoteTags | ForEach-Object {
                if ($_ -match 'refs/tags/(.*)$' -and $matches[1] -notmatch '\^\{\}$') {
                    $matches[1]
                }
            } | Where-Object { $_ } | Sort-Object { [Version]($_ -replace '^v', '') } -Descending | Select-Object -First 10
        }
    }
    
    if ($githubReleases -and $githubReleases.Count -gt 0) {
        Write-Host "🚀 Последние релизы на GitHub:" -ForegroundColor Green
        foreach ($release in $githubReleases) {
            try {
                # Пытаемся распарсить дату в ISO 8601 формате
                $publishDate = [DateTime]::ParseExact($release.publishedAt, "yyyy-MM-ddTHH:mm:ssZ", [System.Globalization.CultureInfo]::InvariantCulture).ToString("dd.MM.yyyy HH:mm")
            }
            catch {
                # Если не получилось, просто берем строку как есть
                $publishDate = $release.publishedAt
            }
            
            if ($release.tagName -eq "v$newVersion") {
                Write-Host "  → $($release.tagName) - $($release.name) ($publishDate) (НОВЫЙ)" -ForegroundColor Green
            }
            else {
                Write-Host "  → $($release.tagName) - $($release.name) ($publishDate)" -ForegroundColor White
            }
        }
        
        # Проверяем, есть ли наш новый релиз
        $newReleaseExists = $githubReleases | Where-Object { $_.tagName -eq "v$newVersion" }
        if ($newReleaseExists) {
            Write-Host "✅ Новый релиз v$newVersion успешно создан на GitHub!" -ForegroundColor Green
        }
        else {
            Write-Host "⏳ Релиз v$newVersion ещё обрабатывается GitHub..." -ForegroundColor Yellow
            Write-Host "   Проверьте через несколько минут: https://github.com/$TARGET_GITHUB_REPO/releases" -ForegroundColor Gray
        }
    }
    else {
        Write-Host "ℹ️  Релизы не найдены (возможно, нужна настройка GitHub Actions)" -ForegroundColor Gray
    }
    
    # Показываем теги с GitHub
    Write-Host ""
    Write-Host "🏷️  Последние теги на GitHub:" -ForegroundColor Yellow
    if ($githubTags) {
        foreach ($tag in $githubTags) {
            if ($tag -eq "v$newVersion") {
                Write-Host "  → $tag (НОВЫЙ)" -ForegroundColor Green
            }
            else {
                Write-Host "  → $tag" -ForegroundColor White
            }
        }
    }
    else {
        Write-Host "  Не удалось получить теги с GitHub" -ForegroundColor Gray
    }
}
catch {
    Write-Host "⚠️  Не удалось получить информацию с GitHub: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "   Попробуйте выполнить: git fetch --tags origin" -ForegroundColor Gray
}

Write-Host ""
Write-Host "🌐 GitHub Repository: https://github.com/$TARGET_GITHUB_REPO/releases" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan


