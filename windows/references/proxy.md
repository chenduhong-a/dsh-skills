---
name: proxy-toggle
description: 临时开关 Windows 系统代理，用于访问被墙的源（github.com / raw.githubusercontent.com / ghproxy 等）。需要翻墙时调用，用完恢复原状。无需管理员权限，改的是 HKCU 用户级注册表。
---

# 代理开关

本机代理：Clash 系，系统代理 `127.0.0.1:7897`（HKCU 注册表，用户级，**不需要管理员**）。

## 三步

### 1. 读原值 → 开

```powershell
$k = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
$orig = Get-ItemProperty $k
"原值: ProxyEnable=$($orig.ProxyEnable) ProxyServer=$($orig.ProxyServer)"
Set-ItemProperty $k -Name ProxyEnable -Value 1
Set-ItemProperty $k -Name ProxyServer -Value '127.0.0.1:7897'
Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class WinINetP{[DllImport("wininet.dll")]public static extern bool InternetSetOption(IntPtr h,int o,IntPtr b,int l);}'
[WinINetP]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0) | Out-Null
$env:HTTP_PROXY='http://127.0.0.1:7897'; $env:HTTPS_PROXY='http://127.0.0.1:7897'
```

### 2. 验证

```powershell
try { (Invoke-WebRequest 'https://github.com' -UseBasicParsing -TimeoutSec 12).StatusCode } catch { "FAIL: $($_.Exception.Message)" }
```

### 3. 恢复原值

```powershell
Set-ItemProperty $k -Name ProxyEnable -Value $orig.ProxyEnable
if ($orig.ProxyServer) { Set-ItemProperty $k -Name ProxyServer -Value $orig.ProxyServer }
[WinINetP]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0) | Out-Null
```

**必须恢复成读到的原值，不是无脑设 0**——用户本来就是开着的话，设 0 等于把人家网络断了。

## 关键坑

1. **`$env:HTTP_PROXY` 只在当前 pwsh 进程有效**。每次调 pwsh 都是新进程，所以**每条命令里都要重设**，不能上一条设了下一条用。
2. **node 的 `fetch` 不读系统代理**（2026-11-02 实测：系统代理开着，node fetch 仍报 `fetch failed`）。`$env:HTTP_PROXY` 对 node 18+ 的 undici fetch 也**不自动生效**。要抓 github 这类被墙地址，**用 PowerShell 的 `Invoke-WebRequest`**（它走系统代理）；要抓 npm registry 这类直连正常的，**用 node fetch 即可**。
3. **`Invoke-WebRequest` 在非交互 PowerShell 里必须加 `-UseBasicParsing`**，否则报「Windows PowerShell 处于非交互模式」。
4. **代理软件没跑时改注册表没用**——先 `Test-NetConnection 127.0.0.1 -Port 7897 -InformationLevel Quiet`，返回 False 就说明 Clash 没开，改注册表也连不上。
5. **广播 `InternetSetOption` 不能省**——不广播的话注册表改了但已运行的程序（含 PowerShell 自己）还用旧设置。

6. **Clash 刚启动时 GitHub API 会报 SSL 未就绪**：`unexpected EOF` / `SSL could not be established` 是预热没走完，不是配置错。启动后**等 10 秒**，失败**最多重试 4 次、间隔 4 秒**，再判失败。
7. **只想查一次就用显式 `-Proxy`，不动注册表**：`Invoke-WebRequest -Proxy http://127.0.0.1:7897 ...` 只让这一条命令走代理，不改 HKCU、不广播、不用恢复原值。查 GitHub 源、抓一两个文件优先走这条。
8. **node 进程的请求不读 WinINet，要 IWR**：`https.get` 与 `fetch` 同属 node 出站（实测证据是 `fetch` 报 `fetch failed`，`HTTP_PROXY` 对 undici 也不自动生效）。抓被墙地址一律 `Invoke-WebRequest -UseBasicParsing`。

## 规矩

- **改代理前在回复里说一声**（「我开一下代理」），不要静默改系统设置。
- **用完恢复原值**。
- 用户手动开关过代理后，下次用之前**重新读原值**，别用缓存。

## 已知事实（2026-11-02 实测）

- 关系统代理 → `github.com` **DNS 解析失败**（「未能解析此远程名称」）——说明这个域名在本机是靠代理才解析得了的
- 开系统代理 → `github.com` **HTTP 200**
- `registry.npmjs.org` **不走代理也通**（所以查 npm 版本/元数据不需要开代理）
- 系统代理是 `127.0.0.1:7897`（Clash 系混合端口，HTTP/SOCKS 共用）
- GitHub API 用几次会 **403 限流**，读文件优先 `raw.githubusercontent.com`

## 7897 不通时：先把 Clash Verge 拉起来（2026-11-09 实测）

代理软件没跑时改注册表没用。本机的客户端是 **Clash Verge**：

```powershell
# 检查
Test-NetConnection 127.0.0.1 -Port 7897 -InformationLevel Quiet
# 启动（注意 exe 名是小写连字符，不是 "Clash Verge.exe"）
Start-Process 'C:\Program Files\Clash Verge\clash-verge.exe'
```

实测启动后 **约 2 秒** 7897 就绪——但**端口通只代表 TCP 起来了，内核与规则集可能还在加载**（2026-11-14 用户纠正：「clash 软件启动要时间预热，别关那么快」），所以端口通后**再等 3–5 秒**才发请求。程序目录 `C:\Program Files\Clash Verge` 下有 `clash-verge.exe`（GUI）、`verge-mihomo.exe` / `verge-mihomo-alpha.exe`（内核），**启动 GUI 那个即可**，内核会自己拉起。

排查顺序：7897 不通 → 看进程（`Get-Process | ? ProcessName -match 'clash|mihomo'`）→ 没进程就启动 → 还是不通说明订阅/配置文件有问题，让用户手动开 GUI 检查。

## 关闭的规矩（2026-11-14 补）

1. **别用完就杀**：请求一结束就 `Stop-Process -Force`，Clash 还没走完自己的收尾，下次启动更慢、状态也可能异常。**等 4–5 秒再关**，或者干脆留着（系统代理恢复原值就够，进程不必杀）。
2. **用户自己开着的 Clash 绝对不要关**——只在「本次是脚本自己拉起来的」情况下收尾，且只关自己拉起的那个。
3. **一次开、全部做完再关**：要抓多个地址/多个文件，合并成一条命令走完，不要每抓一个就开关一轮。
