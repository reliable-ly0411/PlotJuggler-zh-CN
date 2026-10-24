<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="zh_TW" sourcelanguage="en_US">
<context>
    <name>AboutDialog</name>
    <message>
        <location filename="../src/ui/AboutDialog.ui" line="+48"/>
        <source>PlotJuggler 4</source>
        <translation>PlotJuggler 4</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Licensed under the Mozilla Public License 2.0</source>
        <translation>依 Mozilla Public License 2.0 授權</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>&lt;a href=&quot;https://github.com/PlotJuggler/PlotJuggler&quot;&gt;github.com/PlotJuggler/PlotJuggler&lt;/a&gt;</source>
        <translation>&lt;a href=&quot;https://github.com/PlotJuggler/PlotJuggler&quot;&gt;github.com/PlotJuggler/PlotJuggler&lt;/a&gt;</translation>
    </message>
</context>
<context>
    <name>AppLanguage</name>
    <message>
        <location filename="../src/main.cpp" line="+335"/>
        <source>Interface language for this session (zh_CN, zh_TW or en_US).</source>
        <translation>此工作階段的介面語言（zh_CN、zh_TW 或 en_US）。</translation>
    </message>
</context>
<context>
    <name>AppProfile</name>
    <message>
        <location line="+12"/>
        <source>Keep settings and core app data in an isolated absolute directory (not a plugin sandbox).</source>
        <translation>將設定及核心應用程式資料儲存於獨立的絕對路徑目錄中（不是外掛程式沙箱）。</translation>
    </message>
</context>
<context>
    <name>CurveEditor</name>
    <message>
        <location filename="../../pj_plotting/widget/src/CurveEditor.ui" line="+37"/>
        <source>Curves</source>
        <translation>曲線</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Filter...</source>
        <translation>篩選…</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Curves options</source>
        <translation>曲線選項</translation>
    </message>
</context>
<context>
    <name>CurveListPanel</name>
    <message>
        <location filename="../src/ui/CurveListPanel.ui" line="+24"/>
        <source>Datasets</source>
        <translation>資料集</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Datasets options</source>
        <translation>資料集選項</translation>
    </message>
    <message>
        <location line="+24"/>
        <location line="+92"/>
        <source>Filter...</source>
        <translation>篩選…</translation>
    </message>
    <message>
        <location line="-80"/>
        <source>Show/hide plot series</source>
        <translation>顯示或隱藏繪圖序列</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Show/hide 2D image topics</source>
        <translation>顯示或隱藏二維影像主題</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Show/hide 3D scene topics</source>
        <translation>顯示或隱藏三維場景主題</translation>
    </message>
    <message>
        <location line="+44"/>
        <source>Custom Series</source>
        <translation>自訂序列</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Add custom series</source>
        <translation>新增自訂序列</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Edit the selected custom series</source>
        <translation>編輯選取的自訂序列</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Custom series options</source>
        <translation>自訂序列選項</translation>
    </message>
</context>
<context>
    <name>DatasetInfoDialog</name>
    <message>
        <location filename="../src/ui/DatasetInfoDialog.ui" line="+27"/>
        <source>Property</source>
        <translation>屬性</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Value</source>
        <translation>值</translation>
    </message>
</context>
<context>
    <name>DatasetMergeActions</name>
    <message>
        <location filename="../src/DatasetMergeActions.cpp" line="+111"/>
        <source>Merging datasets is a destructive operation. Do you wish to proceed?</source>
        <translation>合併資料集是一項破壞性操作。是否繼續？</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>The following datasets overlap in time:</source>
        <translation>以下資料集的時間範圍重疊：</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>The following datasets have colliding data:</source>
        <translation>以下資料集存在資料衝突：</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>The following datasets contain object topics that will be merged into the result:</source>
        <translation>以下資料集包含物件主題，這些主題將一並合併到結果中：</translation>
    </message>
    <message>
        <location line="+25"/>
        <location line="+40"/>
        <source>Cannot merge datasets</source>
        <translation>無法合併資料集</translation>
    </message>
    <message>
        <location line="-38"/>
        <source>Stop streaming the live source before merging it with other datasets.</source>
        <translation>請先停止接收此即時資料來源，再將其與其他資料集合併。</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>canonical %1</source>
        <translation>標準型別 %1</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>&quot;%1&quot;: %2 vs %3</source>
        <translation>「%1」：%2 與 %3</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>...and %1 more</source>
        <translation>…以及另外 %1 項</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>These object topics share a name but have incompatible types or formats, so the datasets cannot be merged:</source>
        <translation>以下物件主題名稱相同，但型別或格式不相容，因此無法合併資料集：</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Remove or rename the conflicting topic and try again.</source>
        <translation>請移除衝突主題或重新命名後重試。</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Merge datasets</source>
        <translation>合併資料集</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Merge</source>
        <translation>合併</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Cancel</source>
        <translation>取消</translation>
    </message>
</context>
<context>
    <name>DiagnosticsDialog</name>
    <message>
        <location filename="../src/ui/DiagnosticsDialog.ui" line="+16"/>
        <source>Info</source>
        <translation>資訊</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Warning</source>
        <translation>警告</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Error</source>
        <translation>錯誤</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Show only diagnostics from one source</source>
        <translation>僅顯示指定來源的診斷資訊</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Filter messages...</source>
        <translation>篩選訊息…</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Clear</source>
        <translation>清除</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Discard all recorded diagnostics</source>
        <translation>清除全部診斷記錄</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Time</source>
        <translation>時間</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Severity</source>
        <translation>嚴重性</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Source</source>
        <translation>來源</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Message</source>
        <translation>訊息</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Select a row to read the full message</source>
        <translation>選取一列以閱讀完整訊息</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Copy</source>
        <translation>複製</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Copy the selected message to the clipboard</source>
        <translation>將選取的訊息複製到剪貼簿</translation>
    </message>
</context>
<context>
    <name>Dialog</name>
    <message>
        <location filename="../../pj_widgets/src/Dialog.ui" line="+49"/>
        <source>Close</source>
        <translation>關閉</translation>
    </message>
</context>
<context>
    <name>DockToolbar</name>
    <message>
        <location filename="../../pj_plotting/widget/src/DockToolbar.ui" line="+91"/>
        <source>...</source>
        <translation>...</translation>
    </message>
    <message>
        <location line="+94"/>
        <source>Split horizontally</source>
        <translation>水平分割</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>Split vertically</source>
        <translation>垂直分割</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>Fullscreen</source>
        <translation>全螢幕</translation>
    </message>
    <message>
        <location line="+37"/>
        <source>Close Plot Area</source>
        <translation>關閉繪圖區</translation>
    </message>
</context>
<context>
    <name>FilterEditorPanel</name>
    <message>
        <location filename="../../pj_plotting/widget/src/FilterEditorPanel.ui" line="+6"/>
        <source>Filter Editor</source>
        <translation>濾波器編輯器</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>&lt;b&gt;Preview&lt;/b&gt;</source>
        <translation>&lt;b&gt;預覽&lt;/b&gt;</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>AutoZoom</source>
        <translation>自動縮放</translation>
    </message>
    <message>
        <location line="+45"/>
        <source>&lt;b&gt;Source curve:&lt;/b&gt;</source>
        <translation>&lt;b&gt;來源曲線：&lt;/b&gt;</translation>
    </message>
    <message>
        <location line="+45"/>
        <source>Alias:</source>
        <translation>別名：</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Name of the filtered output series (editable)</source>
        <translation>濾波後的輸出序列名稱（可編輯）</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>&lt;b&gt;Transform:&lt;/b&gt;</source>
        <translation>&lt;b&gt;轉換：&lt;/b&gt;</translation>
    </message>
    <message>
        <location line="+93"/>
        <source>Cancel</source>
        <translation>取消</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Save</source>
        <translation>儲存</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Generate time series</source>
        <translation>產生時間序列</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Apply the filter and add the result as a new persistent series in the datastore and curve tree</source>
        <translation>套用濾波器，並將結果新增為資料儲存區及曲線樹中的常駐序列</translation>
    </message>
</context>
<context>
    <name>LeftPanel</name>
    <message>
        <location filename="../src/ui/LeftPanel.ui" line="+31"/>
        <source>Sources</source>
        <translation>資料來源</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>File</source>
        <translation>檔案</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Stream</source>
        <translation>串流資料</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Cloud</source>
        <translation>雲端</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Recent layouts &amp; files</source>
        <translation>最近的版面配置和檔案</translation>
    </message>
    <message>
        <location line="+39"/>
        <source>Load a data file</source>
        <translation>載入資料檔案</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Reload previous data</source>
        <translation>重新載入先前的資料</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>Start streaming</source>
        <translation>開始接收串流資料</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Pause streaming</source>
        <translation>暫停接收串流資料</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Record the subscribed topics of every active stream to an MCAP file</source>
        <translation>將每個作用中的資料串流中已訂閱的主題錄製為 MCAP 檔案</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>Recording: elapsed time, bytes written, and how many messages were dropped because the disk could not keep up</source>
        <translation>錄製狀態：已用時間、已寫入位元組數，以及磁碟寫入速度不足導致的訊息丟棄數</translation>
    </message>
    <message>
        <location line="+24"/>
        <source>Streaming buffer length (seconds)</source>
        <translation>串流資料緩衝時長（秒）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source> sec</source>
        <translation> 秒</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Streaming buffer (seconds)</source>
        <translation>串流資料緩衝（秒）</translation>
    </message>
    <message>
        <location line="+40"/>
        <source>Open cloud browser</source>
        <translation>開啟雲端瀏覽器</translation>
    </message>
</context>
<context>
    <name>MainWindow</name>
    <message>
        <location filename="../src/MainWindow.ui" line="+14"/>
        <source>PlotJuggler 4</source>
        <translation>PlotJuggler 4</translation>
    </message>
    <message>
        <location line="+291"/>
        <source>Extensions Marketplace…</source>
        <translation>擴充功能市場…</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Ctrl+Shift+M</source>
        <translation>Ctrl+Shift+M</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Quit</source>
        <translation>結束</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Ctrl+Q</source>
        <translation>Ctrl+Q</translation>
    </message>
</context>
<context>
    <name>MarketplaceWindow</name>
    <message>
        <location filename="../../pj_marketplace/src/ui/marketplace_window.ui" line="+27"/>
        <source>Data Sources</source>
        <translation>資料來源</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Extensions that load data from files</source>
        <translation>用於從檔案載入資料的擴充功能</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Data Streamers</source>
        <translation>串流資料來源</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Extensions that stream data continuously</source>
        <translation>用於持續接收串流資料的擴充功能</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Parsers</source>
        <translation>解析器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Extensions that decode byte blobs into fields</source>
        <translation>用於將二進位資料解碼為欄位的擴充功能</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Toolboxes</source>
        <translation>工具箱</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Extensions that add a tool with its own GUI</source>
        <translation>提供獨立圖形介面工具的擴充功能</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Installed only</source>
        <translation>僅已安裝</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Show only extensions that are already installed</source>
        <translation>僅顯示已安裝的擴充功能</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Search extensions...</source>
        <translation>搜尋擴充功能…</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Install local...</source>
        <translation>從本機安裝…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Install a plugin from a local ZIP. The archive is not from the registry, so its origin cannot be verified — only that it holds a loadable plugin. Replacing an already-installed extension takes effect on the next restart, unless the archive holds exactly what is already installed, which changes nothing.</source>
        <translation>從本機 ZIP 壓縮檔安裝外掛程式。壓縮檔並非來自擴充功能註冊表，因此無法驗證其來源，只能檢查其中的外掛程式是否能夠載入。替換已安裝的擴充功能將在下次重新啟動時生效；如果壓縮檔內容與已安裝版本完全相同，則不會發生變化。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Update All</source>
        <translation>全部更新</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Update every installed extension that has a newer version available</source>
        <translation>更新所有有新版本可用的已安裝擴充功能</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Plugin settings — open Preferences ▸ Plugins</source>
        <translation>外掛程式設定：開啟「偏好設定 ▸ 外掛程式」</translation>
    </message>
    <message>
        <location line="+46"/>
        <source>font-weight:700; font-size:14px;</source>
        <translation>font-weight:700; font-size:14px;</translation>
    </message>
    <message>
        <location line="+49"/>
        <source>Details</source>
        <translation>詳細資料</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Show marketplace diagnostics</source>
        <translation>顯示擴充功能市場診斷資訊</translation>
    </message>
</context>
<context>
    <name>PJ::AboutDialog</name>
    <message>
        <location filename="../src/ui/AboutDialog.cpp" line="+16"/>
        <source>About PlotJuggler</source>
        <translation>關於 PlotJuggler</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Version %1</source>
        <translation>版本 %1</translation>
    </message>
</context>
<context>
    <name>PJ::ArchiveDiagnostics</name>
    <message>
        <location filename="../../pj_marketplace/src/core/DownloadManager.cpp" line="+31"/>
        <source>archive entry is neither a regular file nor a directory</source>
        <translation>壓縮檔條目既不是普通檔案，也不是目錄</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>archive entry has an empty path</source>
        <translation>壓縮檔條目的路徑為空</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>archive entry path uses a backslash separator</source>
        <translation>壓縮檔條目路徑使用了反斜線分隔字元</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>archive entry path is absolute</source>
        <translation>壓縮檔條目使用了絕對路徑</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>archive entry path carries a drive letter</source>
        <translation>壓縮檔條目路徑包含磁碟機代號</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>archive entry path has an empty segment</source>
        <translation>壓縮檔條目路徑包含空路徑段</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>archive entry path has a dot segment</source>
        <translation>壓縮檔條目路徑包含 . 或 .. 路徑段</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>archive entry path segment ends in a dot or space</source>
        <translation>壓縮檔條目路徑段以點號或空白結尾</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>archive entry path uses a reserved device name</source>
        <translation>壓縮檔條目路徑使用了保留的裝置名</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>archive entry path holds a control byte</source>
        <translation>壓縮檔條目路徑包含控制字元</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>archive holds more than %1 entries</source>
        <translation>壓縮檔包含的條目數超過 %1</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>archive entry expands to more than %1 bytes</source>
        <translation>壓縮檔條目解壓後超過 %1 位元組</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>archive expands to more than %1 bytes in total</source>
        <translation>壓縮檔解壓後的總大小超過 %1 位元組</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>archive entry path is deeper than %1 segments</source>
        <translation>壓縮檔條目路徑的階層超過 %1</translation>
    </message>
</context>
<context>
    <name>PJ::BuiltinFilters</name>
    <message>
        <location filename="../../pj_plotting/widget/src/BuiltinFilterPresentation.cpp" line="+15"/>
        <source>None</source>
        <translation>無</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Pass-through (no change).</source>
        <translation>直接輸出（不變更數值）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Absolute</source>
        <translation>絕對值</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Absolute value |y|.</source>
        <translation>絕對值 |y|。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Scale</source>
        <translation>縮放</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Affine scale + offset, with a time shift.</source>
        <translation>仿射縮放與偏移，並可調整時間位移。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Offset</source>
        <translation>偏移</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Time offset</source>
        <translation>時間偏移</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Derivative</source>
        <translation>微分</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Rate of change dv/dt.</source>
        <translation>變化率 dv/dt。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Use fixed Δt</source>
        <translation>使用固定 Δt</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Fixed Δt</source>
        <translation>固定 Δt</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Integral</source>
        <translation>積分</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Running trapezoidal integral of y over time.</source>
        <translation>使用梯形法累計計算 y 對時間的積分。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Moving Average</source>
        <translation>移動平均</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Boxcar moving average.</source>
        <translation>矩形視窗移動平均。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Window</source>
        <translation>視窗長度</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Center timestamp</source>
        <translation>時間戳記置中</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Moving Root Mean Squared</source>
        <translation>移動均方根</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Moving RMS over a window.</source>
        <translation>計算視窗內的移動均方根。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Moving Variance / Stdev</source>
        <translation>移動變異數 / 標準差</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Moving variance or standard deviation.</source>
        <translation>計算移動變異數或標準差。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Standard deviation</source>
        <translation>標準差</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Outlier Removal</source>
        <translation>離群值剔除</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Drop single-sample spikes.</source>
        <translation>移除僅出現在單一取樣點的尖峰。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Factor</source>
        <translation>系數</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Samples Counter</source>
        <translation>取樣點計數器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Count of samples in a trailing time window.</source>
        <translation>計算截至目前時間的移動視窗內取樣點數。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Binary Filter</source>
        <translation>二值濾波</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Boolean 0/1 predicate over the value.</source>
        <translation>依條件將數值轉換為 0 或 1。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Comparison</source>
        <translation>比較條件</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>== a</source>
        <translation>== a</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&lt; a</source>
        <translation>&lt; a</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&lt;= a</source>
        <translation>&lt;= a</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&gt; a</source>
        <translation>&gt; a</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&gt;= a</source>
        <translation>&gt;= a</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>in [a, b]</source>
        <translation>位於 [a, b] 內</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Threshold a</source>
        <translation>閾值 a</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Threshold b</source>
        <translation>閾值 b</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Tolerance (==)</source>
        <translation>容許誤差（==）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Time Since Previous</source>
        <translation>距上一個取樣點的時間</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Δt between consecutive samples (seconds).</source>
        <translation>相鄰取樣點之間的 Δt（秒）。</translation>
    </message>
</context>
<context>
    <name>PJ::BundledPluginDiagnostics</name>
    <message>
        <location filename="../../pj_widgets/include/pj_widgets/BundledPluginText.h" line="+142"/>
        <source>ArduPilot BIN requires a string filepath</source>
        <translation>ArduPilot BIN 需要字串型別的檔案路徑</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>ArduPilot BIN requires a nonempty filepath without NUL bytes</source>
        <translation>ArduPilot BIN 需要非空且不含 NUL 位元組的檔案路徑</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>ArduPilot BIN: no filepath configured</source>
        <translation>ArduPilot BIN：未設定檔案路徑</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>ArduPilot BIN: cannot open file</source>
        <translation>ArduPilot BIN：無法開啟檔案</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>ArduPilot BIN: unsupported file size</source>
        <translation>ArduPilot BIN：不支援的檔案大小</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>ArduPilot BIN: file read failed or file changed during import</source>
        <translation>ArduPilot BIN：檔案讀取失敗，或檔案在匯入期間發生變化</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>ArduPilot BIN: timestamp exceeds the SDK nanosecond range</source>
        <translation>ArduPilot BIN：時間戳記超出 SDK 支援的奈秒範圍</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>invalid config JSON</source>
        <translation>設定 JSON 無效</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>invalid config</source>
        <translation>設定無效</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>no filepath configured</source>
        <translation>未設定檔案路徑</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>CSV parsing failed</source>
        <translation>CSV 解析失敗</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Loading aborted by user</source>
        <translation>使用者已中止載入</translation>
    </message>
</context>
<context>
    <name>PJ::BundledPluginMetadata</name>
    <message>
        <location line="-147"/>
        <source>Arrow IPC Parser</source>
        <translation>Arrow IPC 解析器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Message parser for self-describing Arrow IPC streams.</source>
        <translation>解析自我描述的 Arrow IPC 資料串流。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>CSV Loader</source>
        <translation>CSV 載入器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Data loader for CSV files.</source>
        <translation>用於 CSV 檔案的資料載入器。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>DataTamer Parser</source>
        <translation>DataTamer 解析器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Message parser for DataTamer encoded data. Efficient serialization for robotics.</source>
        <translation>用於 DataTamer 編碼資料的訊息解析器，支援面向機器人的高效序列化。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Dummy Streamer</source>
        <translation>模擬資料串流</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Generates synthetic sine, cosine, sawtooth, and noise signals for testing and demonstration.</source>
        <translation>產生正弦、餘弦、鋸齒波及雜訊訊號，用於測試與示範。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Foxglove Bridge</source>
        <translation>Foxglove 橋接</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Connect to Foxglove WebSocket server for ROS data streaming. Compatible with Foxglove Studio.</source>
        <translation>連線 Foxglove WebSocket 伺服器以接收 ROS 資料串流，相容 Foxglove Studio。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>JSON Parser</source>
        <translation>JSON 解析器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Message parser for JSON, CBOR, MessagePack, and BSON encoded data.</source>
        <translation>用於 JSON、CBOR、MessagePack 和 BSON 編碼資料的訊息解析器。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>MCAP Loader</source>
        <translation>MCAP 載入器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Data loader for MCAP files and split ROS 2 bags (metadata.yaml). Supports ROS1, ROS2, Protobuf, and JSON message encodings.</source>
        <translation>載入 MCAP 檔案及分卷 ROS 2 資料包（metadata.yaml），支援 ROS1、ROS2、Protobuf 和 JSON 訊息編碼。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>MP4 Loader</source>
        <translation>MP4 載入器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Data loader for .mp4 video files. Reads the container&apos;s creation_time tag (when present) so the host can anchor the video on a wall-clock timeline; supports multi-file selection via the standard File dialog.</source>
        <translation>載入 .mp4 影片檔案。讀取容器的 creation_time 標籤（若存在），使主程式可將影片定位在絕對時間軸上；支援透過標準檔案對話方塊選擇多個檔案。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Parquet Loader</source>
        <translation>Parquet 載入器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Data loader for Apache Parquet files. Efficient columnar storage format.</source>
        <translation>載入 Apache Parquet 檔案，這是一種高效的欄式儲存格式。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>PlotJuggler Bridge</source>
        <translation>PlotJuggler 橋接</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Connect to PlotJuggler Bridge server for generic data streaming over WebSocket.</source>
        <translation>連線 PlotJuggler Bridge 伺服器，透過 WebSocket 接收通用資料串流。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>3D Loader (PLY/PCD)</source>
        <translation>3D 載入器（PLY/PCD）</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Data loader for static 3D files: .pcd and vertex-only .ply load as a point cloud; .ply with faces loads as a 3D mesh. One snapshot at timestamp 0.</source>
        <translation>載入靜態 3D 檔案：.pcd 和僅包含頂點的 .ply 作為點雲載入；包含面的 .ply 作為三維網格載入。在時間戳記 0 處產生一個快照。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Protobuf Parser</source>
        <translation>Protobuf 解析器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Message parser for Protocol Buffers encoded data. Promotes the well-known Foxglove schemas (PointCloud, CompressedVideo, CompressedImage, RawImage, ImageAnnotations, SceneUpdate, FrameTransform, PosesInFrame, CameraCalibration, VoxelGrid, Grid) to builtin scene objects.</source>
        <translation>解析 Protocol Buffers 編碼訊息，將常用 Foxglove 訊息型別（PointCloud、CompressedVideo、CompressedImage、RawImage、ImageAnnotations、SceneUpdate、FrameTransform、PosesInFrame、CameraCalibration、VoxelGrid、Grid）轉換為內建場景物件。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>ROS CDR Parser</source>
        <translation>ROS CDR 解析器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Message parser for ROS1 and ROS2 messages (ros1msg, ros2msg, omgidl). Promotes common sensor and visualization messages (Image, PointCloud2, OccupancyGrid, GridMap, TF, Markers, and yolo_msgs/DetectionArray to ImageAnnotations) to builtin scene objects.</source>
        <translation>解析 ROS1 和 ROS2 訊息（ros1msg、ros2msg、omgidl），將常用感測器及視覺化訊息（Image、PointCloud2、OccupancyGrid、GridMap、TF、Markers，以及轉換為 ImageAnnotations 的 yolo_msgs/DetectionArray）轉換為內建場景物件。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>ROS 2 Topic Subscriber</source>
        <translation>ROS 2 主題訂閱器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Subscribe to ROS 2 topics in real time and stream the decoded fields into PlotJuggler.</source>
        <translation>即時訂閱 ROS 2 主題，並將解碼欄位以資料串流形式傳入 PlotJuggler。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Assistant Agent</source>
        <translation>智慧型助手</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>A chat assistant that drives PlotJuggler through the plugin SDK: lists and describes topics, reads series statistics, and creates derived timeseries, markers and plot tabs it owns. Uses the Claude Code or Codex CLI already installed and signed in on your machine; the plugin stores no API keys. Linux, macOS and Windows.</source>
        <translation>透過外掛程式 SDK 操作 PlotJuggler 的聊天助手，可列出及描述主題、讀取序列統計資訊，並建立其擁有的衍生時間序列、標記和繪圖分頁。使用您電腦上已安裝並登入的 Claude Code 或 Codex 命令列工具；外掛程式不儲存 API 金鑰。支援 Linux、macOS 和 Windows。</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Mosaico Cloud Server</source>
        <translation>Mosaico 雲端伺服器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Browse and import data from Mosaico cloud servers via Apache Arrow Flight. Scalar topics are handed to the host as arrow-ipc messages and decoded by the parser_arrow plugin (install it alongside). Includes Lua metadata predicate filter, multi-topic streaming, and time-range selection.</source>
        <translation>透過 Apache Arrow Flight 瀏覽並匯入 Mosaico 雲端伺服器資料。純量主題以 arrow-ipc 訊息交給主程式，由 parser_arrow 外掛程式解碼（需同時安裝）。支援 Lua 中繼資料條件篩選、多主題串流傳輸和時間範圍選擇。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Quaternion to RPY</source>
        <translation>四元數轉 RPY</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Converts quaternion (x, y, z, w) time series into Roll, Pitch, Yaw angles with optional unwrapping and degree/radian output.</source>
        <translation>將四元數（x、y、z、w）時間序列轉換為滾轉、俯仰及偏航角，可選擇展開角度，並以角度或弧度輸出。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Transform Editor</source>
        <translation>轉換編輯器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Create named derived time series using Lua functions. Equivalent to the Custom Series editor in PJ3.</source>
        <translation>使用 Lua 函式建立命名的衍生時間序列，相當於 PJ3 的自訂序列編輯器。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>ULog Loader</source>
        <translation>ULog 載入器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Data loader for PX4 ULog files. Flight log format for PX4 autopilot.</source>
        <translation>載入 PX4 ULog 檔案，這是 PX4 自動駕駛儀的飛行記錄檔格式。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>WebRTC Video Client</source>
        <translation>WebRTC 影片用戶端</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Receives live H.264 video via standard WHEP (mediamtx, go2rtc, LiveKit, Cloudflare Stream...) and feeds each stream to PlotJuggler as canonical PJ.VideoFrame messages. One HTTP request per stream, per-camera reconnect, mediamtx Control API discovery. H.264 pass-through; no transcode.</source>
        <translation>透過標準 WHEP 接收即時 H.264 影片（mediamtx、go2rtc、LiveKit、Cloudflare Stream 等），並以標準 PJ.VideoFrame 訊息送入 PlotJuggler。每路串流使用一次 HTTP 要求，支援逐攝影機重新連線及 mediamtx Control API 發現。H.264 直接傳輸，不轉碼。</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>ArduPilot DataFlash BIN logs: numeric fields, sensor instances, units, parameters and message timelines.</source>
        <translation>ArduPilot DataFlash BIN 記錄檔：數值欄位、感測器執行個體、單位、參數及訊息時間軸。</translation>
    </message>
</context>
<context>
    <name>PJ::BundledPlugins</name>
    <message>
        <location filename="../../pj_dialog_host/src/bundled_translation_entries.hpp" line="+29"/>
        <source>Select ROS messages</source>
        <translation>選擇 ROS 訊息</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Scanning ROS 2 topics...</source>
        <translation>正在掃描 ROS 2 主題…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Topic Selector</source>
        <translation>主題選擇器</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+46"/>
        <source>If present, use the timestamp in the field [header.stamp]</source>
        <translation>如果存在，則使用 [header.stamp] 欄位中的時間戳記</translation>
    </message>
    <message>
        <location line="-45"/>
        <location line="+46"/>
        <location line="+83"/>
        <location line="+12"/>
        <source>Maximum size of arrays:</source>
        <translation>陣列大小上限：</translation>
    </message>
    <message>
        <location line="-140"/>
        <location line="+46"/>
        <location line="+83"/>
        <location line="+12"/>
        <source>clamp</source>
        <translation>截斷</translation>
    </message>
    <message>
        <location line="-140"/>
        <location line="+46"/>
        <location line="+83"/>
        <location line="+12"/>
        <source>discard</source>
        <translation>丟棄</translation>
    </message>
    <message>
        <location line="-140"/>
        <source>Filter: </source>
        <translation>篩選： </translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Tip: [CTRL+A] select all, [CTRL+SHIFT+A] deselect all</source>
        <translation>提示：[CTRL+A] 全選，[CTRL+SHIFT+A] 取消全選</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Advanced Options</source>
        <translation>進階選項</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+43"/>
        <source>String parsing (used for instance in diagnostic_msgs/DiagnosticArray)</source>
        <translation>字串解析（例如用於 diagnostic_msgs/DiagnosticArray）</translation>
    </message>
    <message>
        <location line="-42"/>
        <location line="+43"/>
        <source>remove suffixes from numbers (example: &quot;100ms&quot; -&gt; 100)</source>
        <translation>移除數字的後綴（例如：&quot;100ms&quot; -&gt; 100）</translation>
    </message>
    <message>
        <location line="-42"/>
        <location line="+43"/>
        <source>convert boolean strings (&quot;false&quot;/&quot;true&quot;) to numbers (0/1)</source>
        <translation>將布林字串（&quot;false&quot;/&quot;true&quot;）轉換為數字（0/1）</translation>
    </message>
    <message>
        <location line="-42"/>
        <source>WebRTC Video Client (WHEP)</source>
        <translation>WebRTC 影片用戶端（WHEP）</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+137"/>
        <location line="+28"/>
        <source>Connection</source>
        <translation>連線</translation>
    </message>
    <message>
        <location line="-164"/>
        <location line="+137"/>
        <location line="+31"/>
        <source>Transport</source>
        <translation>傳輸方式</translation>
    </message>
    <message>
        <location line="-167"/>
        <location line="+137"/>
        <location line="+28"/>
        <source>Address</source>
        <translation>位址</translation>
    </message>
    <message>
        <location line="-164"/>
        <location line="+137"/>
        <location line="+28"/>
        <source>Port</source>
        <translation>連接埠</translation>
    </message>
    <message>
        <location line="-164"/>
        <source>Server</source>
        <translation>伺服器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>WHEP signaling is HTTP. (HTTPS is not wired in this build.)</source>
        <translation>WHEP 訊號交換使用 HTTP。（此建置版本尚未支援 HTTPS。）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>WHEP server host (mediamtx). Each selected path is read from http://&lt;address&gt;:&lt;port&gt;/&lt;path&gt;/whep.</source>
        <translation>WHEP 伺服器主機（mediamtx）。每個選取路徑均從 http://&lt;address&gt;:&lt;port&gt;/&lt;path&gt;/whep 讀取。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>WHEP server port (mediamtx default 8889).</source>
        <translation>WHEP 伺服器連接埠（mediamtx 預設為 8889）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Control API</source>
        <translation>控制 API</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Control API is HTTP. (HTTPS is not wired in this build.)</source>
        <translation>Control API 使用 HTTP。（此建置版本尚未支援 HTTPS。）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>mediamtx Control API host, used only to list paths (GET /v3/paths/list). Auto-derived from the server; edit to override, or clear to disable API discovery (manual paths still work).</source>
        <translation>mediamtx 控制 API 主機，僅用於列出路徑（GET /v3/paths/list）。預設根據伺服器自動推導；可編輯以覆寫，或清除以停用 API 發現（手動路徑仍可使用）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>mediamtx Control API port (default 9997).</source>
        <translation>mediamtx 控制 API 連接埠（預設為 9997）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Refresh list</source>
        <translation>重新整理清單</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Base path</source>
        <translation>基礎路徑</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Optional base path prefix on the server (most mediamtx setups leave this empty).</source>
        <translation>伺服器上的可選基礎路徑前綴（大多數 mediamtx 設定可留空）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+3"/>
        <source>(optional)</source>
        <translation>（可選）</translation>
    </message>
    <message>
        <location line="-2"/>
        <source>Bearer token</source>
        <translation>Bearer 權杖</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Optional. Sent as &quot;Authorization: Bearer ...&quot; on every WHEP and Control API request.</source>
        <translation>可選。每個 WHEP 和控制 API 要求都會以 &quot;Authorization: Bearer ...&quot; 的形式傳送此權杖。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Topic prefix</source>
        <translation>主題前綴</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Each selected path becomes the topic &lt;prefix&gt;/&lt;path&gt;.</source>
        <translation>每個選取路徑都會成為主題 &lt;prefix&gt;/&lt;path&gt;。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Streams</source>
        <translation>串流</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+125"/>
        <location line="+24"/>
        <source>Filter</source>
        <translation>篩選</translation>
    </message>
    <message>
        <location line="-148"/>
        <source>Paths on the server (from the Control API) plus manually added ones. Select the streams you want; each becomes its own PJ.VideoFrame topic. Only H.264 streams are selectable.</source>
        <translation>列出伺服器上的路徑（由 Control API 提供）及手動新增的路徑。請選取所需的串流，每個串流都會成為獨立的 PJ.VideoFrame 主題。僅能選取 H.264 串流。</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+440"/>
        <source>Path</source>
        <translation>路徑</translation>
    </message>
    <message>
        <location line="-439"/>
        <location line="+440"/>
        <source>Tracks</source>
        <translation>軌道</translation>
    </message>
    <message>
        <location line="-439"/>
        <location line="+440"/>
        <source>Ready</source>
        <translation>就緒</translation>
    </message>
    <message>
        <location line="-439"/>
        <source>Manual path:</source>
        <translation>手動路徑：</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Add a path the Control API did not list (API disabled, or a non-mediamtx WHEP server).</source>
        <translation>新增控制 API 未列出的路徑（適用於 API 已停用或非 mediamtx 的 WHEP 伺服器）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Add</source>
        <translation>新增</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>ICE Servers (STUN / TURN)</source>
        <translation>ICE 伺服器（STUN / TURN）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>STUN: fill URL only (e.g. stun:stun.l.google.com:19302). TURN: also fill Username and Credential (e.g. turn:turn.example.org:3478).</source>
        <translation>STUN：僅填寫 URL（例如 stun:stun.l.google.com:19302）。TURN：還需填寫使用者名稱和認證資訊（例如 turn:turn.example.org:3478）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+435"/>
        <source>Username</source>
        <translation>使用者名稱</translation>
    </message>
    <message>
        <location line="-434"/>
        <location line="+435"/>
        <source>Credential</source>
        <translation>認證資訊</translation>
    </message>
    <message>
        <location line="-434"/>
        <source>ROS Parser Options</source>
        <translation>ROS 解析器選項</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Server Certificate / API Key</source>
        <translation>伺服器憑證／API 金鑰</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Server:</source>
        <translation>伺服器：</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+97"/>
        <location line="+25"/>
        <source>Connect</source>
        <translation>連線</translation>
    </message>
    <message>
        <location line="-121"/>
        <source>Cert / API Key…</source>
        <translation>憑證／API 金鑰…</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+262"/>
        <location line="+1"/>
        <source>Sequences</source>
        <translation>序列</translation>
    </message>
    <message>
        <location line="-262"/>
        <location line="+8"/>
        <source>Filter…</source>
        <translation>篩選…</translation>
    </message>
    <message>
        <location line="-7"/>
        <location line="+8"/>
        <source>Use regular expression</source>
        <translation>使用正規表示式</translation>
    </message>
    <message>
        <location line="-7"/>
        <source>Reload sequences</source>
        <translation>重新載入序列</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Metadata Filter</source>
        <translation>中繼資料篩選</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Key</source>
        <translation>鍵</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Op</source>
        <translation>運算子</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+98"/>
        <location line="+3"/>
        <location line="+302"/>
        <location line="+2"/>
        <source>Value</source>
        <translation>值</translation>
    </message>
    <message>
        <location line="-404"/>
        <location line="+116"/>
        <location line="+142"/>
        <location line="+1"/>
        <source>Topics</source>
        <translation>主題</translation>
    </message>
    <message>
        <location line="-256"/>
        <source>Reload topics</source>
        <translation>重新載入主題</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+91"/>
        <location line="+165"/>
        <location line="+1"/>
        <source>Info</source>
        <translation>資訊</translation>
    </message>
    <message>
        <location line="-256"/>
        <location line="+37"/>
        <source>Cancel</source>
        <translation>取消</translation>
    </message>
    <message>
        <location line="-36"/>
        <source>Download</source>
        <translation>下載</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Quaternion to RPY</source>
        <translation>四元數轉 RPY</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Radians</source>
        <translation>弧度</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Degrees</source>
        <translation>度</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Unwrap Angles</source>
        <translation>展開角度</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Save</source>
        <translation>儲存</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>MCAP Parser</source>
        <translation>MCAP 解析器</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+21"/>
        <source>Settings</source>
        <translation>設定</translation>
    </message>
    <message>
        <location line="-20"/>
        <source>If an array size exceeds:</source>
        <translation>如果陣列大小超過：</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>then:</source>
        <translation>則：</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+73"/>
        <source>Clamp</source>
        <translation>截斷</translation>
    </message>
    <message>
        <location line="-72"/>
        <location line="+73"/>
        <source>Skip</source>
        <translation>跳過</translation>
    </message>
    <message>
        <location line="-72"/>
        <source>Timestamp:</source>
        <translation>時間戳記：</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>publish</source>
        <translation>發佈時間</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>log</source>
        <translation>記錄時間</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Override with the message header timestamp (if present)</source>
        <translation>使用訊息標頭中的時間戳記覆寫（如果存在）</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+70"/>
        <source>Channels</source>
        <translation>通道</translation>
    </message>
    <message>
        <location line="-69"/>
        <source>Filter Channel Names</source>
        <translation>篩選通道名稱</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Select All</source>
        <translation>全選</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Deselect All</source>
        <translation>取消全選</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+207"/>
        <source>Channel name</source>
        <translation>通道名稱</translation>
    </message>
    <message>
        <location line="-206"/>
        <location line="+207"/>
        <source>Schema</source>
        <translation>結構定義</translation>
    </message>
    <message>
        <location line="-206"/>
        <location line="+200"/>
        <location line="+7"/>
        <source>Encoding</source>
        <translation>編碼</translation>
    </message>
    <message>
        <location line="-206"/>
        <location line="+207"/>
        <source>Msg Count</source>
        <translation>訊息數</translation>
    </message>
    <message>
        <location line="-206"/>
        <source>Rename conversation</source>
        <translation>重新命名對話</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Name (leave blank to use the default title)</source>
        <translation>名稱（留空則使用預設標題）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Assistant Agent</source>
        <translation>智慧型助手</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Settings...</source>
        <translation>設定…</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Conversations</source>
        <translation>對話</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>New chat: start a fresh conversation (the current one stays in this list)</source>
        <translation>新增對話：開始一段新對話（目前對話將保留在此清單中）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>rename=Rename</source>
        <translation>rename=重新命名</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Ask the assistant to list your topics, describe a topic, or plot the derivative of a series...</source>
        <translation>讓助手列出主題、描述某個主題，或繪製某個序列的導數…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Ready.</source>
        <translation>就緒。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Type a message and press Send...</source>
        <translation>輸入訊息並按「傳送」…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Send</source>
        <translation>傳送</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Assistant Agent - Settings</source>
        <translation>智慧型助手 - 設定</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Choose which model backend the assistant uses.</source>
        <translation>選擇助手使用的模型後端。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Backend</source>
        <translation>後端</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Claude Code (subscription)</source>
        <translation>Claude Code（訂閱）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Codex (ChatGPT subscription)</source>
        <translation>Codex（ChatGPT 訂閱）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Claude model</source>
        <translation>Claude 模型</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+5"/>
        <source>Custom model</source>
        <translation>自訂模型</translation>
    </message>
    <message>
        <location line="-4"/>
        <location line="+5"/>
        <source>full model name</source>
        <translation>完整模型名稱</translation>
    </message>
    <message>
        <location line="-4"/>
        <source>claude CLI path</source>
        <translation>claude 命令列工具路徑</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>claude (on PATH) or full path</source>
        <translation>claude（位於 PATH 中）或完整路徑</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Codex model</source>
        <translation>Codex 模型</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>codex CLI path</source>
        <translation>codex 命令列工具路徑</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>codex (on PATH) or full path</source>
        <translation>codex（位於 PATH 中）或完整路徑</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>JSON Parser Options</source>
        <translation>JSON 解析器選項</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+14"/>
        <source>Use embedded timestamp field</source>
        <translation>使用內嵌時間戳記欄位</translation>
    </message>
    <message>
        <location line="-13"/>
        <source>If enabled, the parser will look for a timestamp field in the JSON message and use its value as the message timestamp.</source>
        <translation>啟用後，解析器將在 JSON 訊息中尋找時間戳記欄位，並將其值用作訊息時間戳記。</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+14"/>
        <source>Timestamp field name:</source>
        <translation>時間戳記欄位名稱：</translation>
    </message>
    <message>
        <location line="-13"/>
        <source>Name of the top-level JSON field containing the timestamp, in seconds.</source>
        <translation>包含時間戳記的頂層 JSON 欄位名稱，時間戳記單位為秒。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Key arrays of labeled objects by label</source>
        <translation>使用標籤作為帶標籤物件陣列的鍵</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>If enabled, arrays of objects carrying a string &quot;label&quot; (or &quot;name&quot;) member are keyed by that label instead of the array index, and a lone &quot;value&quot; member collapses onto it (e.g. scalars/shoulder_pan.pos instead of scalars[0]/value).</source>
        <translation>啟用後，對於含有字串 &quot;label&quot;（或 &quot;name&quot;）成員的物件陣列，將使用該標籤而非陣列索引作為鍵；如果僅有一個 &quot;value&quot; 成員，則將其合併到該鍵下（例如，使用 scalars/shoulder_pan.pos，而不是 scalars[0]/value）。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Protobuf Parser Options</source>
        <translation>Protobuf 解析器選項</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Proto file:</source>
        <translation>Proto 檔案：</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Path to a .proto file</source>
        <translation>.proto 檔案的路徑</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Browse for a .proto file</source>
        <translation>瀏覽並選擇 .proto 檔案</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Select your message type:</source>
        <translation>選擇訊息型別：</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>If enabled, the parser will look for a top-level double field and use its value (in seconds) as the message timestamp.</source>
        <translation>啟用後，解析器將尋找頂層 double 型別欄位，並將其值（單位為秒）用作訊息時間戳記。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Name of the top-level double field containing the timestamp in seconds. Leave empty to try &quot;timestamp&quot; then &quot;ts&quot; automatically.</source>
        <translation>包含時間戳記（單位為秒）的頂層 double 型別欄位名稱。留空時將自動依次嘗試 &quot;timestamp&quot; 和 &quot;ts&quot;。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>File text:</source>
        <translation>檔案文字：</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Proto file content will appear here after loading...</source>
        <translation>載入後將在此處顯示 Proto 檔案內容…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Include Folders</source>
        <translation>引入檔案資料夾</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>When an array size exceeds:</source>
        <translation>當陣列大小超過：</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Use the timestamp in the message (if present)</source>
        <translation>使用訊息中的時間戳記（如果存在）</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>ULog File</source>
        <translation>ULog 檔案</translation>
    </message>
    <message>
        <location line="+2"/>
        <location line="+3"/>
        <location line="+302"/>
        <location line="+2"/>
        <source>Property</source>
        <translation>屬性</translation>
    </message>
    <message>
        <location line="-305"/>
        <source>Properties</source>
        <translation>屬性</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Message Logs</source>
        <translation>訊息記錄檔</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+303"/>
        <source>Timestamp</source>
        <translation>時間戳記</translation>
    </message>
    <message>
        <location line="-302"/>
        <location line="+303"/>
        <source>Level</source>
        <translation>等級</translation>
    </message>
    <message>
        <location line="-302"/>
        <location line="+303"/>
        <source>Message</source>
        <translation>訊息</translation>
    </message>
    <message>
        <location line="-302"/>
        <source>Parquet Loader</source>
        <translation>Parquet 載入器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Parse Date Format</source>
        <translation>解析日期格式</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Visit &lt;a href=&quot;https://doc.qt.io/qt-5/qtime.html#toString&quot;&gt;&lt;span style=&quot; text-decoration: underline; color:#0000ff;&quot;&gt;these&lt;/span&gt;&lt;/a&gt; &lt;a href=&quot;https://doc.qt.io/qt-5/qdate.html#fromString-2&quot;&gt;&lt;span style=&quot; text-decoration: underline; color:#0000ff;&quot;&gt;links&lt;/span&gt;&lt;/a&gt; to learn more about the Date-Time format&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;存取&lt;a href=&quot;https://doc.qt.io/qt-5/qtime.html#toString&quot;&gt;&lt;span style=&quot; text-decoration: underline; color:#0000ff;&quot;&gt;時間格式說明&lt;/span&gt;&lt;/a&gt;和&lt;a href=&quot;https://doc.qt.io/qt-5/qdate.html#fromString-2&quot;&gt;&lt;span style=&quot; text-decoration: underline; color:#0000ff;&quot;&gt;日期格式說明&lt;/span&gt;&lt;/a&gt;，瞭解日期時間格式的更多資訊。&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Select a column to be used as timestamp</source>
        <translation>選取用作時間戳記的欄</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Use row number as X axis</source>
        <translation>使用列號作為 X 軸</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Columns:</source>
        <translation>欄：</translation>
    </message>
    <message>
        <location line="+8"/>
        <location line="+108"/>
        <location line="+4"/>
        <source>Topic Name</source>
        <translation>主題名稱</translation>
    </message>
    <message>
        <location line="-111"/>
        <location line="+108"/>
        <location line="+4"/>
        <source>DataType</source>
        <translation>資料型別</translation>
    </message>
    <message>
        <location line="-111"/>
        <source>Name of the Function</source>
        <translation>函式名稱</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Name:</source>
        <translation>名稱：</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Warning</source>
        <translation>警告</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>A function with the same name exists already in the list of saved functions.

Overwrite it?</source>
        <translation>已儲存的函式清單中已存在同名函式。

是否覆寫？</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Transform Editor</source>
        <translation>轉換編輯器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Single Function</source>
        <translation>單函式</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+18"/>
        <source>Input Timeseries</source>
        <translation>輸入時間序列</translation>
    </message>
    <message>
        <location line="-17"/>
        <location line="+1"/>
        <location line="+27"/>
        <source>Help</source>
        <translation>說明</translation>
    </message>
    <message>
        <location line="-26"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Drag &amp;amp; drop timeseries here. Pick the radio to set which one is &lt;span style=&quot; font-weight:600;&quot;&gt;value&lt;/span&gt;.&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;將時間序列拖放到此處。透過單選按鈕選擇用作 &lt;span style=&quot; font-weight:600;&quot;&gt;value&lt;/span&gt; 的序列。&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+16"/>
        <source>Global Variables</source>
        <translation>全域變數</translation>
    </message>
    <message>
        <location line="-15"/>
        <location line="+16"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Portion of code outside the function.&lt;/p&gt;&lt;p&gt;Useful to add global variables.&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;函式之外的程式碼部分。&lt;/p&gt;&lt;p&gt;可用於新增全域變數。&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="-15"/>
        <location line="+16"/>
        <source>Add your global variables here</source>
        <translation>在此新增全域變數</translation>
    </message>
    <message>
        <location line="-15"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Import functions from a XML library.&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;從 XML 庫匯入函式。&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Export functions from a XML library.&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;從 XML 庫匯出函式。&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Save the current function in the library.&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;將目前函式儲存到庫中。&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Browse and manage available functions.&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;瀏覽和管理可用函式。&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+12"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Write your function implementation here. &lt;/p&gt;&lt;p&gt;It &lt;span style=&quot; font-weight:600;&quot;&gt;must&lt;/span&gt; return a new value.&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;在此編寫函式實作。&lt;/p&gt;&lt;p&gt;函式&lt;span style=&quot; font-weight:600;&quot;&gt;必須&lt;/span&gt;傳回一個新值。&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="-11"/>
        <location line="+12"/>
        <source>Write your function here</source>
        <translation>在此編寫函式</translation>
    </message>
    <message>
        <location line="-11"/>
        <source>Output Timeseries</source>
        <translation>輸出時間序列</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>name the new timeseries</source>
        <translation>為新時間序列命名</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&lt;html&gt;&lt;body&gt;&lt;p&gt;Name of the new time series.&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;body&gt;&lt;p&gt;新時間序列的名稱。&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+12"/>
        <location line="+190"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+6"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Create New Time Series</source>
        <translation>建立新時間序列</translation>
    </message>
    <message>
        <location line="-213"/>
        <source>Batch Functions</source>
        <translation>批量函式</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Drag &amp;amp; drop timeseries here. The function is applied to each one separately.&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;將時間序列拖放到此處。函式將分別套用於每個序列。&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Prefix</source>
        <translation>前綴</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Suffix</source>
        <translation>後綴</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>prefix / suffix to add to the names</source>
        <translation>要新增到名稱中的前綴／後綴</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>&lt;!DOCTYPE HTML PUBLIC &quot;-//W3C//DTD HTML 4.0//EN&quot; &quot;http://www.w3.org/TR/REC-html40/strict.dtd&quot;&gt;
&lt;html&gt;&lt;head&gt;&lt;meta name=&quot;qrichtext&quot; content=&quot;1&quot; /&gt;&lt;style type=&quot;text/css&quot;&gt;
p, li { white-space: pre-wrap; }
&lt;/style&gt;&lt;/head&gt;&lt;body style=&quot; font-family:&apos;Ubuntu&apos;; font-size:11pt; font-weight:400; font-style:normal;&quot;&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-size:14pt; font-weight:600;&quot;&gt;Transform editor Help&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:14pt; font-weight:600;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;The transform editor uses the scripting language Lua. You may want to read &lt;a href=&quot;http://tylerneylon.com/a/learn-lua/&quot;&gt;&lt;span style=&quot; text-decoration: underline;&quot;&gt;Learn Lua in 15 minutes&lt;/span&gt;&lt;/a&gt;.&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;In practice, you don&apos;t need to know that much to use it in PlotJuggler.&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;You should implement the body of a &lt;span style=&quot; font-style:italic;&quot;&gt;function(time, value),&lt;/span&gt; that is invoked for each point. The returned value is the point [time, your_value]&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-size:12pt; font-weight:600;&quot;&gt;Single input, stateless functions:&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;Example:&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return (value *  2) + 1&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;or you can use the &lt;a href=&quot;https://www.tutorialspoint.com/lua/lua_math_library.htm&quot;&gt;&lt;span style=&quot; text-decoration: underline;&quot;&gt;math library from Lua&lt;/span&gt;&lt;/a&gt;:&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return math.log(value)&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;The new point will have the same time of the original point. If you want to modify the timestamp, just return two values like this:&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return time +1, (value *  2) &lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-size:12pt; font-weight:600;&quot;&gt;Return multiple points at once:&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;Since version 3.1, you may also return multiple values at once, using a Lua table:&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   -- Calculate t1,v1, t2, v2, etc...&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return { {t1, v1}, {t2, v2} }&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-size:12pt; font-weight:600;&quot;&gt;Stateful functions:&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;Some transformations require some form of &amp;quot;memory&amp;quot;, i.e. they need the previous value. To do this you may use the &amp;quot;global variable&amp;quot; textbox.&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;For instance, to compute the finite difference between two consecutive value, you would add this to the &lt;span style=&quot; font-weight:600;&quot;&gt;Global Variables&lt;/span&gt; textbox:&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   prev = nil&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;And this to the &lt;span style=&quot; font-weight:600;&quot;&gt;Function() &lt;/span&gt;textbox&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   if ( prev == nil ) then&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;        prev = value&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   end&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   diff = value - prev&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   prev = value&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return diff  &lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-size:12pt; font-weight:600;&quot;&gt;Multi input, single output:&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;Select an additional time series and drop it in the table on the left side. Now your function definition will look like &lt;span style=&quot; font-style:italic;&quot;&gt;function(time,value,v1)&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;Average of two time series:&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return (value + v1) / 2&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;!DOCTYPE HTML PUBLIC &quot;-//W3C//DTD HTML 4.0//EN&quot; &quot;http://www.w3.org/TR/REC-html40/strict.dtd&quot;&gt;
&lt;html&gt;&lt;head&gt;&lt;meta name=&quot;qrichtext&quot; content=&quot;1&quot; /&gt;&lt;style type=&quot;text/css&quot;&gt;
p, li { white-space: pre-wrap; }
&lt;/style&gt;&lt;/head&gt;&lt;body style=&quot; font-family:'Ubuntu'; font-size:11pt; font-weight:400; font-style:normal;&quot;&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-size:14pt; font-weight:600;&quot;&gt;轉換編輯器說明&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:14pt; font-weight:600;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;轉換編輯器使用 Lua 指令碼語言。您可以先閱讀&lt;a href=&quot;http://tylerneylon.com/a/learn-lua/&quot;&gt;&lt;span style=&quot; text-decoration: underline;&quot;&gt;15 分鐘學會 Lua&lt;/span&gt;&lt;/a&gt;.&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;實際上，在 PlotJuggler 中使用它並不需要掌握太多知識。&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;您需要實作以下函式的函式主體：&lt;span style=&quot; font-style:italic;&quot;&gt;function(time, value),&lt;/span&gt;它會對每個資料點呼叫一次。傳回值將構成資料點 [time, your_value]。&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-size:12pt; font-weight:600;&quot;&gt;單輸入、無狀態函式：&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;範例：&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return (value *  2) + 1&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;也可以使用 &lt;a href=&quot;https://www.tutorialspoint.com/lua/lua_math_library.htm&quot;&gt;&lt;span style=&quot; text-decoration: underline;&quot;&gt;Lua 數學庫&lt;/span&gt;&lt;/a&gt;:&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return math.log(value)&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;新資料點的時間與原資料點相同。如果需要修改時間戳記，只需像下面這樣傳回兩個值：&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return time +1, (value *  2) &lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-size:12pt; font-weight:600;&quot;&gt;一次傳回多個資料點：&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;從 3.1 版本起，還可以使用 Lua 表一次傳回多個值：&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   -- Calculate t1,v1, t2, v2, etc...&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return { {t1, v1}, {t2, v2} }&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-size:12pt; font-weight:600;&quot;&gt;有狀態函式：&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;某些轉換需要某種形式的「記憶」，即需要前一個值。為此，可以使用「全域變數」文字框。&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;例如，要計算兩個相鄰值的有限差分，可以在&lt;span style=&quot; font-weight:600;&quot;&gt;全域變數&lt;/span&gt;文字框中新增以下程式碼：&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   prev = nil&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;並在 &lt;span style=&quot; font-weight:600;&quot;&gt;Function() &lt;/span&gt;文字框中新增以下程式碼：&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   if ( prev == nil ) then&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;        prev = value&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   end&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   diff = value - prev&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   prev = value&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return diff  &lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot;-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;br /&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-size:12pt; font-weight:600;&quot;&gt;多輸入、單輸出：&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;選擇另一個時間序列並將其拖放到左側表格中。此時，函式定義將變為 &lt;span style=&quot; font-style:italic;&quot;&gt;function(time,value,v1)&lt;/span&gt;&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;計算兩個時間序列的平均值：&lt;/p&gt;
&lt;p style=&quot; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;&quot;&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;   return (value + v1) / 2&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Function Library</source>
        <translation>函式庫</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Functions</source>
        <translation>函式</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Search</source>
        <translation>搜尋</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+15"/>
        <source>Preview</source>
        <translation>預覽</translation>
    </message>
    <message>
        <location line="-14"/>
        <source>Ctrl+Click to select multiple</source>
        <translation>按住 Ctrl 並按一下可多選</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Use</source>
        <translation>使用</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>CSV Loader</source>
        <translation>CSV 載入器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Delimiter</source>
        <translation>分隔字元</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+7"/>
        <source>Detect Automatically</source>
        <translation>自動偵測</translation>
    </message>
    <message>
        <location line="-6"/>
        <source>Delimiter:</source>
        <translation>分隔字元：</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+44"/>
        <source>&quot;,&quot; (comma)</source>
        <translation>&quot;,&quot;（逗號）</translation>
    </message>
    <message>
        <location line="-43"/>
        <location line="+44"/>
        <source>&quot;;&quot; (semicolon)</source>
        <translation>&quot;;&quot;（分號）</translation>
    </message>
    <message>
        <location line="-43"/>
        <location line="+44"/>
        <source>&quot; &quot; (space)</source>
        <translation>&quot; &quot;（空白）</translation>
    </message>
    <message>
        <location line="-43"/>
        <location line="+44"/>
        <source>&quot;\t&quot; (tab)</source>
        <translation>&quot;\t&quot;（定位字元）</translation>
    </message>
    <message>
        <location line="-43"/>
        <source>Timestamp Format</source>
        <translation>時間戳記格式</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Custom</source>
        <translation>自訂</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Time Axis</source>
        <translation>時間軸</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Table</source>
        <translation>表格</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Raw</source>
        <translation>原始內容</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Date-Time Format</source>
        <translation>日期時間格式</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Common Format Examples (input date: 1/15/2024 2:30:45.123 PM)</source>
        <translation>常見格式範例（輸入日期：1/15/2024 2:30:45.123 PM）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Format String</source>
        <translation>格式字串</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Result</source>
        <translation>結果</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>All other input characters will be treated as text. Any non-empty sequence of characters enclosed in single quotes will also be treated (stripped of the quotes) as text and not be interpreted as expressions.</source>
        <translation>所有其他輸入字元均視為文字。任何用單引號括起來的非空字元序列也將視為文字（去掉引號），不會被解釋為運算式。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Date Format</source>
        <translation>日期格式</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+13"/>
        <source>Expression</source>
        <translation>運算式</translation>
    </message>
    <message>
        <location line="-12"/>
        <location line="+13"/>
        <source>Output</source>
        <translation>輸出</translation>
    </message>
    <message>
        <location line="-12"/>
        <source>The day as a number without a leading zero (1 to 31)</source>
        <translation>日期中的日，不帶前導零（1 至 31）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The day as a number with a leading zero (01 to 31)</source>
        <translation>日期中的日，帶前導零（01 至 31）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The abbreviated localized day name (e.g. &apos;Mon&apos; to &apos;Sun&apos;)</source>
        <translation>在地化的星期簡稱（例如 'Mon' 至 'Sun'）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The long localized day name (e.g. &apos;Monday&apos; to &apos;Sunday&apos;)</source>
        <translation>在地化的星期全稱（例如 'Monday' 至 'Sunday'）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The month as a number without a leading zero (1 to 12)</source>
        <translation>月份，不帶前導零（1 至 12）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The month as a number with a leading zero (01 to 12)</source>
        <translation>月份，帶前導零（01 至 12）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The abbreviated localized month name (e.g. &apos;Jan&apos; to &apos;Dec&apos;)</source>
        <translation>在地化的月份簡稱（例如 'Jan' 至 'Dec'）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The long localized month name (e.g. &apos;January&apos; to &apos;December&apos;)</source>
        <translation>在地化的月份全稱（例如 'January' 至 'December'）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The year as a two digit number (00 to 99)</source>
        <translation>兩位數字的年份（00 至 99）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The year as a four digit number, possibly plus a leading minus sign for negative years</source>
        <translation>四位數字的年份；負年份前可能帶有負號</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Time Format</source>
        <translation>時間格式</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>The hour without a leading zero (0 to 23 or 1 to 12 if AM/PM display)</source>
        <translation>小時，不帶前導零（0 至 23；採用 AM/PM 顯示時為 1 至 12）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The hour with a leading zero (00 to 23 or 01 to 12 if AM/PM display)</source>
        <translation>小時，帶前導零（00 至 23；採用 AM/PM 顯示時為 01 至 12）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The hour without a leading zero (0 to 23, even with AM/PM display)</source>
        <translation>小時，不帶前導零（0 至 23，即使採用 AM/PM 顯示也不變）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The hour with a leading zero (00 to 23, even with AM/PM display)</source>
        <translation>小時，帶前導零（00 至 23，即使採用 AM/PM 顯示也不變）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The minute without a leading zero (0 to 59)</source>
        <translation>分鐘，不帶前導零（0 至 59）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The minute with a leading zero (00 to 59)</source>
        <translation>分鐘，帶前導零（00 至 59）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The whole second, without any leading zero (0 to 59)</source>
        <translation>整數秒，不帶前導零（0 至 59）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The whole second, with a leading zero where applicable (00 to 59)</source>
        <translation>整數秒，必要時帶前導零（00 至 59）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The fractional part of the second, to go after a decimal point, without trailing zeroes (0 to 999). Thus &quot;s.z&quot; reports the seconds to full available (millisecond) precision without trailing zeroes.</source>
        <translation>秒的小數部分，位於小數點之後，不帶末尾零（0 至 999）。因此，&quot;s.z&quot; 以完整的可用精度（毫秒）顯示秒數，不帶末尾零。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The fractional part of the second, to millisecond precision, including trailing zeroes where applicable (000 to 999).</source>
        <translation>秒的小數部分，精確到毫秒，必要時包含末尾零（000 至 999）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Interpret as an AM/PM time. A/AP will match an upper-case version of either QLocale::amText() or QLocale::pmText().</source>
        <translation>按 AM/PM 時間解釋。A/AP 將符合 QLocale::amText() 或 QLocale::pmText() 的大寫形式。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Interpret as an am/pm time. a/ap will match a lower-case version of either QLocale::amText() or QLocale::pmText().</source>
        <translation>按 am/pm 時間解釋。a/ap 將符合 QLocale::amText() 或 QLocale::pmText() 的小寫形式。</translation>
    </message>
    <message>
        <location line="+5"/>
        <location line="+1"/>
        <source>Number of Rows</source>
        <translation>列數</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <source>Selected Column</source>
        <translation>所選欄</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <source>Multiple Columns</source>
        <translation>多欄組合</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <source>Duplicate column names detected. Adding suffixes</source>
        <translation>偵測到重複欄名，將新增後綴</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <source>Some rows have column number mismatch. Will skip those</source>
        <translation>部分列的欄數不符，將略過這些列</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+4"/>
        <source>Connected</source>
        <translation>已連線</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Click to select, Click+Drag to multi-select</source>
        <translation>按一下選擇，按一下並拖曳可多選</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>No channels were found in this MCAP file.</source>
        <translation>此 MCAP 檔案中未找到任何通道。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Select Proto File</source>
        <translation>選擇 Proto 檔案</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>(load a .proto file first)</source>
        <translation>（請先載入 .proto 檔案）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Select Include Folder</source>
        <translation>選取引入檔案資料夾</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Add folders where imported .proto files can be found:</source>
        <translation>新增用於尋找匯入的 .proto 檔案的資料夾：</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <source>invalid syntax</source>
        <translation>語法無效</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+5"/>
        <location line="+1"/>
        <source>Name</source>
        <translation>名稱</translation>
    </message>
    <message>
        <location line="-5"/>
        <location line="+1"/>
        <source>Date</source>
        <translation>日期</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+3"/>
        <location line="+1"/>
        <source>Size</source>
        <translation>大小</translation>
    </message>
    <message>
        <location line="+3"/>
        <location line="+1"/>
        <source>Topics — loading…</source>
        <translation>主題：載入中…</translation>
    </message>
    <message>
        <location line="+5"/>
        <location line="+1"/>
        <source>Download progress</source>
        <translation>下載進度</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Server URI contains invalid characters (control or non-ASCII bytes).</source>
        <translation>伺服器 URI 包含無效字元（控制字元或非 ASCII 位元組）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>TLS certificate path contains invalid characters.</source>
        <translation>TLS 憑證路徑包含無效字元。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>API key contains invalid characters (control or non-ASCII bytes).</source>
        <translation>API 金鑰包含無效字元（控制字元或非 ASCII 位元組）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Reloading sequences…</source>
        <translation>正在重新載入序列…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Reloading topics…</source>
        <translation>正在重新載入主題…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Credentials saved</source>
        <translation>認證資訊已儲存</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Select a sequence + topic(s) first</source>
        <translation>請先選擇一個序列和主題</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Cancelling…</source>
        <translation>正在取消…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Download cancelled — kept the topics that finished first</source>
        <translation>下載已取消，已保留此前完成的主題</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Download cancelled</source>
        <translation>下載已取消</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>host offers no parser ingest (arrow-ipc topics need a newer PlotJuggler)</source>
        <translation>主程式不支援解析器匯入（arrow-ipc 主題需要較新版本的 PlotJuggler）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Unknown error</source>
        <translation>未知錯誤</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>not connected</source>
        <translation>未連線</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>topic row count overflow</source>
        <translation>主題列數溢位</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>host not bound</source>
        <translation>主程式未繫結</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>no data in the requested range</source>
        <translation>要求範圍內沒有資料</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>pull failed: unknown error</source>
        <translation>擷取失敗：未知錯誤</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Drag and Drop Quaternion values in the frames above.</source>
        <translation>請將四元數值拖放到上方的輸入框中。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Created roll/pitch/yaw transform.</source>
        <translation>已建立 roll/pitch/yaw 轉換。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>host did not expose pj.data_processors.v1</source>
        <translation>主程式未提供 pj.data_processors.v1</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Input timeseries</source>
        <translation>輸入時間序列</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Var</source>
        <translation>變數</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+36"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Drag &amp; drop timeseries here</source>
        <translation>將時間序列拖放到此處</translation>
    </message>
    <message>
        <location line="-39"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Function</source>
        <translation>函式</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Language</source>
        <translation>語言</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+6"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Snippet library (*.json)</source>
        <translation>程式碼片段庫 (*.json)</translation>
    </message>
    <message>
        <location line="-9"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Import snippet library</source>
        <translation>匯入程式碼片段庫</translation>
    </message>
    <message>
        <location line="+6"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Export snippet library</source>
        <translation>匯出程式碼片段庫</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Name is required</source>
        <translation>名稱不能為空</translation>
    </message>
    <message>
        <location line="+6"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+5"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Modify Time Series</source>
        <translation>修改時間序列</translation>
    </message>
    <message>
        <location line="+5"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Create a name for the new series
</source>
        <translation>請為新序列命名
</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Give the new series a name that isn&apos;t one of its inputs
</source>
        <translation>新序列的名稱不能與任何輸入序列相同
</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Add an input time series (drag &amp; drop)
</source>
        <translation>請拖放以新增輸入時間序列
</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Write your function body
</source>
        <translation>請撰寫函式主體
</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>The selected file contains no functions.</source>
        <translation>所選檔案中沒有函式。</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Could not read a function library from the selected file.</source>
        <translation>無法從所選檔案中讀取函式庫。</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Could not write the selected file.</source>
        <translation>無法寫入所選檔案。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Transform Editor: a source series, an output name, and a function body are required.</source>
        <translation>轉換編輯器：必須提供來源序列、輸出名稱和函式主體。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Transform Editor: the host did not expose pj.data_processors.v1 (cannot create the series).</source>
        <translation>轉換編輯器：主程式未提供 pj.data_processors.v1（無法建立序列）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Transform Editor: no valid output name.</source>
        <translation>轉換編輯器：沒有有效的輸出名稱。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Transform Editor: drop in some input series, set a prefix/suffix, and write a function body.</source>
        <translation>轉換編輯器：請拖入輸入序列，設定前綴或後綴，並編寫函式主體。</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Topic</source>
        <translation>主題</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Datatype</source>
        <translation>資料型別</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>path not added: whitespace/control characters are not allowed</source>
        <translation>未新增路徑：不允許包含空白或控制字元</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>No conversations yet</source>
        <translation>暫無對話</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>CLI default</source>
        <translation>CLI 預設值</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Custom...</source>
        <translation>自訂…</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>sonnet — fast; the measured default</source>
        <translation>sonnet：快速；經實測的預設選項</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>quaternion apply failed: host did not expose pj.data_processors.v1</source>
        <translation>套用四元數失敗：主程式未提供 pj.data_processors.v1</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>quaternion save failed: host did not expose pj.data_processors.v1</source>
        <translation>四元數儲存失敗：主程式未提供 pj.data_processors.v1</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Output:</source>
        <translation>輸出：</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>e.g. /imu/rpy/</source>
        <translation>例如 /imu/rpy/</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>e.g. cam0</source>
        <translation>例如 cam0</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <source>e.g. timestamp, ts, time</source>
        <translation>例如 timestamp, ts, time</translation>
    </message>
    <message>
        <location line="+15"/>
        <location line="+1"/>
        <source>Values in &quot;%1&quot; are not monotonically increasing. Will sort these automatically</source>
        <translation>「%1」欄中的值並非單調遞增，將自動排序</translation>
    </message>
    <message>
        <location line="-2"/>
        <source>No readable channels: all %1 channel(s) in this file reference a missing schema.</source>
        <translation>沒有可讀取的通道：此檔案中的全部 %1 個通道皆參照了不存在的結構定義。</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Cannot open this MCAP file.%1
Code: %2
Message: %3</source>
        <translation>無法開啟此 MCAP 檔案。%1
錯誤碼：%2
訊息：%3</translation>
    </message>
    <message>
        <location line="-2"/>
        <source>Cannot read the contents of this MCAP file.%1
Code: %2
Message: %3</source>
        <translation>無法讀取此 MCAP 檔案的內容。%1
錯誤碼：%2
訊息：%3</translation>
    </message>
    <message>
        <location line="+33"/>
        <source>Cannot open %1</source>
        <translation>無法開啟 %1</translation>
    </message>
    <message>
        <location line="-27"/>
        <source>Not a ROS 2 bag metadata.yaml: %1</source>
        <translation>不是 ROS 2 bag 的 metadata.yaml：%1</translation>
    </message>
    <message>
        <location line="-22"/>
        <source>Only MCAP-storage ROS 2 bags are supported; this bag uses &apos;%1&apos;. Convert it with &apos;ros2 bag convert&apos; (storage_id: mcap).</source>
        <translation>僅支援使用 MCAP 儲存的 ROS 2 bag；此 bag 使用「%1」。請使用 'ros2 bag convert' 轉換（storage_id: mcap）。</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>The ROS 2 bag metadata lists no data files: %1</source>
        <translation>ROS 2 bag 中繼資料未列出任何資料檔案：%1</translation>
    </message>
    <message>
        <location line="-5"/>
        <source>Only MCAP-storage ROS 2 bags are supported; unsupported bag file: %1</source>
        <translation>僅支援使用 MCAP 儲存的 ROS 2 bag；不支援的 bag 檔案：%1</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>ROS 2 bag file listed in metadata.yaml is missing: %1</source>
        <translation>metadata.yaml 中列出的 ROS 2 bag 檔案缺失：%1</translation>
    </message>
    <message>
        <location line="+34"/>
        <location line="+1"/>
        <source>Info — %1</source>
        <translation>資訊：%1</translation>
    </message>
    <message>
        <location line="-8"/>
        <source>Connecting to %1…</source>
        <translation>正在連線到 %1…</translation>
    </message>
    <message>
        <location line="-3"/>
        <source>Fetching %1 topic(s)…</source>
        <translation>正在取得 %1 個主題…</translation>
    </message>
    <message>
        <location line="-17"/>
        <source>Mosaico connection failed: %1</source>
        <translation>Mosaico 連線失敗：%1</translation>
    </message>
    <message>
        <location line="+26"/>
        <source>%1 sequences</source>
        <translation>%1 個序列</translation>
    </message>
    <message>
        <location line="-21"/>
        <source>Mosaico fetch errors:
%1</source>
        <translation>Mosaico 取得錯誤：
%1</translation>
    </message>
    <message>
        <location line="-2"/>
        <source>Imported %1/%2 topics from %3</source>
        <translation>已從 %3 匯入 %1/%2 個主題</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Connected — server %1</source>
        <translation>已連線，伺服器版本 %1</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>listTopics %1: %2</source>
        <translation>列出主題 %1：%2</translation>
    </message>
    <message>
        <location line="-32"/>
        <source>synthetic timestamp overflows int64 at row %1 (anchor %2, interval %3)</source>
        <translation>產生的時間戳記在第 %1 列超出 int64 範圍（起點 %2，間隔 %3）</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>create dataset failed: %1</source>
        <translation>建立資料集失敗：%1</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>pull failed: %1</source>
        <translation>擷取失敗：%1</translation>
    </message>
    <message>
        <location line="-3"/>
        <source>Create failed: %1</source>
        <translation>建立失敗：%1</translation>
    </message>
    <message>
        <location line="-19"/>
        <source>quaternion save failed: %1</source>
        <translation>四元數儲存失敗：%1</translation>
    </message>
    <message>
        <location line="-1"/>
        <source>quaternion apply failed: %1</source>
        <translation>套用四元數失敗：%1</translation>
    </message>
    <message>
        <location line="+5"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Imported %1 function(s).</source>
        <translation>已匯入 %1 個函式。</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>Exported %1 function(s).</source>
        <translation>已匯出 %1 個函式。</translation>
    </message>
    <message>
        <location line="-33"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>function produced no output — declared %1 output, so it must return exactly %1 value per point</source>
        <translation>函式未產生輸出：已宣告 %1 個輸出，因此每個點必須恰好傳回 %1 個值</translation>
    </message>
    <message>
        <location line="-9"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <location line="+1"/>
        <source>function produced no output — declared %1 outputs, so it must return exactly %1 values per point</source>
        <translation>函式未產生輸出：已宣告 %1 個輸出，因此每個點必須恰好傳回 %1 個值</translation>
    </message>
    <message>
        <location line="+38"/>
        <source>Transform Editor: %1</source>
        <translation>轉換編輯器：%1</translation>
    </message>
    <message>
        <location line="-22"/>
        <source>Transform Editor: created %1 series.</source>
        <translation>轉換編輯器：已建立 %1 個序列。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Transform Editor: error on &apos;%1&apos;: %2</source>
        <translation>轉換編輯器：處理「%1」時出錯：%2</translation>
    </message>
    <message>
        <location line="+23"/>
        <source>%1 topic(s) found</source>
        <translation>找到 %1 個主題</translation>
    </message>
    <message>
        <location line="-6"/>
        <source>%1 path(s) on the server</source>
        <translation>伺服器上有 %1 個路徑</translation>
    </message>
    <message>
        <location line="-20"/>
        <source>Control API: %1 (manual paths still work)</source>
        <translation>控制 API：%1（仍可使用手動路徑）</translation>
    </message>
</context>
<context>
    <name>PJ::CalendarWidget</name>
    <message>
        <location filename="../../pj_widgets/src/DateRangePicker.cpp" line="+298"/>
        <source>Mon</source>
        <translation>週一</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Tue</source>
        <translation>週二</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Wed</source>
        <translation>週三</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Thu</source>
        <translation>週四</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Fri</source>
        <translation>週五</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Sat</source>
        <translation>週六</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Sun</source>
        <translation>週日</translation>
    </message>
</context>
<context>
    <name>PJ::Colormap</name>
    <message>
        <location filename="../../pj_widgets/src/Colormap.cpp" line="+166"/>
        <location line="+8"/>
        <source>Turbo</source>
        <translation>Turbo</translation>
    </message>
    <message>
        <location line="-6"/>
        <source>Viridis</source>
        <translation>Viridis</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Plasma</source>
        <translation>Plasma</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Grayscale</source>
        <translation>灰階</translation>
    </message>
</context>
<context>
    <name>PJ::CredentialsEditor</name>
    <message>
        <location filename="../../pj_widgets/src/CredentialsEditor.cpp" line="+64"/>
        <source>Browse...</source>
        <translation>瀏覽…</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Certificate:</source>
        <translation>憑證：</translation>
    </message>
    <message>
        <location line="+11"/>
        <location line="+17"/>
        <source>Show</source>
        <translation>顯示</translation>
    </message>
    <message>
        <location line="-9"/>
        <source>API Key:</source>
        <translation>API 金鑰：</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Allow insecure / plaintext connection</source>
        <translation>允許不安全或明文連線</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Hide</source>
        <translation>隱藏</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Select certificate</source>
        <translation>選擇憑證</translation>
    </message>
</context>
<context>
    <name>PJ::CurveEditor</name>
    <message>
        <location filename="../../pj_plotting/widget/src/CurveEditor.cpp" line="+258"/>
        <source>Clear all curves</source>
        <translation>清除所有曲線</translation>
    </message>
    <message>
        <location line="+210"/>
        <source>Dataset markers</source>
        <translation>資料集標記</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Global markers</source>
        <translation>全域標記</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>%1 — %2</source>
        <translation>%1 — %2</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>Toggle curve visibility</source>
        <translation>顯示或隱藏曲線</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Toggle marker visibility</source>
        <translation>顯示或隱藏標記</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Remove this curve from its plot</source>
        <translation>從圖表中移除此曲線</translation>
    </message>
    <message>
        <location line="+58"/>
        <source>Show or hide this dataset&apos;s markers on this plot</source>
        <translation>在此圖表中顯示或隱藏此資料集的標記</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Show or hide this dataset&apos;s global markers on this plot</source>
        <translation>在此圖表中顯示或隱藏此資料集的全域標記</translation>
    </message>
</context>
<context>
    <name>PJ::CurveListPanel</name>
    <message>
        <location filename="../src/ui/CurveListPanel.cpp" line="+289"/>
        <source>Show Values</source>
        <translation>顯示數值</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Preserve Topic Name</source>
        <translation>保留主題名稱</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Remove all Datasets</source>
        <translation>移除全部資料集</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>No series match the current search or type filters.</source>
        <translation>沒有符合目前搜尋條件或型別篩選的序列。</translation>
    </message>
    <message>
        <location line="+33"/>
        <source>Delete</source>
        <translation>刪除</translation>
    </message>
    <message>
        <location line="+96"/>
        <source>Not subscribed. Drop it into a view to start streaming.</source>
        <translation>尚未訂閱。拖入檢視即可開始接收串流資料。</translation>
    </message>
    <message>
        <location line="+9"/>
        <location line="+18"/>
        <source>&lt;span style=&quot;font-weight:600&quot;&gt;Type:&lt;/span&gt; %1</source>
        <translation>&lt;span style=&quot;font-weight:600&quot;&gt;型別：&lt;/span&gt; %1</translation>
    </message>
    <message>
        <location line="-16"/>
        <source>&lt;span style=&quot;font-weight:600&quot;&gt;Messages:&lt;/span&gt; %1</source>
        <translation>&lt;span style=&quot;font-weight:600&quot;&gt;訊息數：&lt;/span&gt; %1</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>&lt;span style=&quot;font-weight:600&quot;&gt;Samples:&lt;/span&gt; %1</source>
        <translation>&lt;span style=&quot;font-weight:600&quot;&gt;取樣數：&lt;/span&gt; %1</translation>
    </message>
    <message>
        <location line="+27"/>
        <source>&lt;span style=&quot;font-weight:600&quot;&gt;Topics:&lt;/span&gt; %1</source>
        <translation>&lt;span style=&quot;font-weight:600&quot;&gt;主題數：&lt;/span&gt; %1</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>&lt;span style=&quot;font-weight:600&quot;&gt;Loader metadata:&lt;/span&gt; %1</source>
        <translation>&lt;span style=&quot;font-weight:600&quot;&gt;載入器中繼資料：&lt;/span&gt; %1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Right-click for Info…</source>
        <translation>右鍵查看資訊…</translation>
    </message>
    <message>
        <location line="+64"/>
        <source>%1 topics were left out of the drag: no view can display them.</source>
        <translation>拖曳時已跳過 %1 個主題：沒有檢視能夠顯示它們。</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>&quot;%1&quot; was left out of the drag: no view can display it.</source>
        <translation>拖曳時已跳過「%1」：沒有檢視能夠顯示它。</translation>
    </message>
    <message>
        <location line="+244"/>
        <source>Info</source>
        <translation>資訊</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Merge</source>
        <translation>合併</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Reload</source>
        <translation>重新載入</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Replace</source>
        <translation>替換</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Remove</source>
        <translation>移除</translation>
    </message>
    <message>
        <location line="+75"/>
        <source>Stop forced streaming</source>
        <translation>停止強制接收串流資料</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Force topic streaming</source>
        <translation>強制接收主題串流資料</translation>
    </message>
</context>
<context>
    <name>PJ::CurveTreeView</name>
    <message>
        <location filename="../../pj_widgets/src/CurveTreeView.cpp" line="+312"/>
        <source>Name</source>
        <translation>名稱</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Value</source>
        <translation>值</translation>
    </message>
    <message>
        <location line="+959"/>
        <source>Stop loading and keep the data received so far</source>
        <translation>停止載入並保留已接收的資料</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Stop loading and discard the partial data</source>
        <translation>停止載入並丟棄已接收的資料</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>This source can stop but cannot discard partial data</source>
        <translation>此資料來源可以停止，但無法丟棄已接收的資料</translation>
    </message>
</context>
<context>
    <name>PJ::DatasetInfoDialog</name>
    <message>
        <location filename="../src/ui/DatasetInfoDialog.cpp" line="+101"/>
        <source>Dataset Info</source>
        <translation>資料集資訊</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Name</source>
        <translation>名稱</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>File</source>
        <translation>檔案</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Provenance</source>
        <translation>來源資訊</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Provider</source>
        <translation>提供者</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Identity</source>
        <translation>識別資訊</translation>
    </message>
    <message>
        <location line="+6"/>
        <location line="+4"/>
        <source>Descriptor</source>
        <translation>描述資訊</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Loader metadata</source>
        <translation>載入器中繼資料</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Loader metadata (%1)</source>
        <translation>載入器中繼資料（%1）</translation>
    </message>
</context>
<context>
    <name>PJ::DateRangePicker</name>
    <message>
        <location filename="../../pj_widgets/src/DateRangePicker.cpp" line="+551"/>
        <source>All</source>
        <translation>全部</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Past 24h</source>
        <translation>過去 24 小時</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Last 7 Days</source>
        <translation>最近 7 天</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Last Month</source>
        <translation>最近一個月</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Custom</source>
        <translation>自訂</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Pick a custom date range</source>
        <translation>選擇自訂日期範圍</translation>
    </message>
    <message>
        <location line="+87"/>
        <source>Close</source>
        <translation>關閉</translation>
    </message>
</context>
<context>
    <name>PJ::DepthImageLayer</name>
    <message>
        <location filename="../../pj_scene2D/widgets/src/layers/depth_image_layer.cpp" line="+105"/>
        <source>Turbo</source>
        <translation>Turbo</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Viridis</source>
        <translation>Viridis</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Plasma</source>
        <translation>Plasma</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Grayscale</source>
        <translation>灰階</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Invert colormap</source>
        <translation>反轉色彩對映</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Colormap</source>
        <translation>色彩對映</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Near</source>
        <translation>近端</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Far</source>
        <translation>遠端</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Auto-fit range</source>
        <translation>自動調整範圍</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Set Near/Far from the current frame&apos;s depth distribution (2–98%)</source>
        <translation>根據目前影格的深度分布（第 2–98 百分位）設定近端和遠端</translation>
    </message>
</context>
<context>
    <name>PJ::DiagnosticsDialog</name>
    <message>
        <location filename="../src/ui/DiagnosticsDialog.cpp" line="+56"/>
        <source>Error</source>
        <translation>錯誤</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Warning</source>
        <translation>警告</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Info</source>
        <translation>資訊</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Diagnostics</source>
        <translation>診斷資訊</translation>
    </message>
    <message>
        <location line="+129"/>
        <source>All sources</source>
        <translation>全部來源</translation>
    </message>
</context>
<context>
    <name>PJ::DockWidget</name>
    <message>
        <location filename="../../pj_plotting/widget/src/DockWidget.cpp" line="+89"/>
        <source>Plot</source>
        <translation>繪圖</translation>
    </message>
    <message>
        <location line="+809"/>
        <source>Copy</source>
        <translation>複製</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Paste</source>
        <translation>貼上</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Split Horizontally</source>
        <translation>水平分割</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Split Vertically</source>
        <translation>垂直分割</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Clear</source>
        <translation>清除</translation>
    </message>
</context>
<context>
    <name>PJ::ExtensionCatalogService</name>
    <message>
        <location filename="../../pj_runtime/src/ExtensionCatalogService.cpp" line="+818"/>
        <source>All supported files</source>
        <translation>所有支援的檔案</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>All files</source>
        <translation>所有檔案</translation>
    </message>
</context>
<context>
    <name>PJ::ExtensionManager</name>
    <message>
        <location filename="../../pj_marketplace/src/core/ExtensionManager.cpp" line="+980"/>
        <source>Not available for this platform (%1)</source>
        <translation>此平台不可用（%1）</translation>
    </message>
</context>
<context>
    <name>PJ::FileDialog</name>
    <message>
        <location filename="../../pj_widgets/src/FileDialog.cpp" line="+63"/>
        <source>Binary file</source>
        <translation>二進位檔案</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>XML document</source>
        <translation>XML 文件</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Plain text document</source>
        <translation>純文字文件</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>CSV document</source>
        <translation>CSV 文件</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>ZIP archive</source>
        <translation>ZIP 壓縮檔</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>%1 file</source>
        <translation>%1 檔案</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>Open File</source>
        <translation>開啟檔案</translation>
    </message>
</context>
<context>
    <name>PJ::FileLoader</name>
    <message>
        <location filename="../src/FileLoader.cpp" line="+1052"/>
        <location line="+1"/>
        <source>Load Data</source>
        <translation>載入資料</translation>
    </message>
    <message>
        <location line="+30"/>
        <location line="+3"/>
        <source>Replace Data</source>
        <translation>替換資料</translation>
    </message>
    <message>
        <location line="+24"/>
        <source>Could not stage the selected file.</source>
        <translation>無法暫存選取的檔案。</translation>
    </message>
    <message>
        <location line="+93"/>
        <source>File has no extension; cannot pick a plugin.</source>
        <translation>檔案沒有副檔名，無法選擇外掛程式。</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>No DataSource plugin handles %1 files. Install one from the Marketplace.</source>
        <translation>沒有可處理 %1 檔案的資料來源外掛程式。請從擴充功能市場安裝。</translation>
    </message>
    <message>
        <location line="+41"/>
        <source>(unspecified)</source>
        <translation>（未指定）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The layout requires DataSource plugin &apos;%1&apos;, but it is not installed for %2 files.</source>
        <translation>此版面配置需要資料來源外掛程式「%1」，但尚未安裝用於處理 %2 檔案的該外掛程式。</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Plugin &apos;%1&apos;: createHandle failed.</source>
        <translation>外掛程式「%1」：createHandle 失敗。</translation>
    </message>
    <message>
        <location line="+23"/>
        <source>Could not create the time domain for %1.</source>
        <translation>無法為 %1 建立時間域。</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Replacement target dataset %1 no longer exists.</source>
        <translation>要替換的目標資料集 %1 已不存在。</translation>
    </message>
    <message>
        <location line="+74"/>
        <source>createDataset failed: %1</source>
        <translation>createDataset 失敗：%1</translation>
    </message>
    <message>
        <location line="+41"/>
        <source>Plugin &apos;%1&apos;: service registration failed: %2</source>
        <translation>外掛程式「%1」：服務註冊失敗：%2</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Plugin &apos;%1&apos;: bind failed: %2</source>
        <translation>外掛程式「%1」：繫結失敗：%2</translation>
    </message>
    <message>
        <location line="+32"/>
        <source>Plugin &apos;%1&apos; rejected the layout&apos;s saved configuration: %2</source>
        <translation>外掛程式「%1」拒絕了版面配置中儲存的設定：%2</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Layout preset rejected by &apos;%1&apos;: %2 — falling back to dialog</source>
        <translation>「%1」拒絕了版面配置預設：%2；將改為顯示設定對話方塊</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Plugin &apos;%1&apos;: loadConfig failed: %2</source>
        <translation>外掛程式「%1」：loadConfig 失敗：%2</translation>
    </message>
    <message>
        <location line="+33"/>
        <source>Plugin contract violation: %1. Reinstall the plugin from the Marketplace.</source>
        <translation>外掛程式介面契約違規：%1。請從擴充功能市場重新安裝此外掛程式。</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>Plugin &apos;%1&apos;: loadConfig (post-dialog) failed: %2</source>
        <translation>外掛程式「%1」：對話方塊關閉後 loadConfig 失敗：%2</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Load cancelled</source>
        <translation>載入已取消</translation>
    </message>
    <message>
        <location line="+23"/>
        <source>Cannot replace dataset %1: the selected configuration expands into %2 datasets.</source>
        <translation>無法替換資料集 %1：選取的設定會產生 %2 個資料集。</translation>
    </message>
    <message>
        <location line="+521"/>
        <location line="+416"/>
        <source>Plugin &apos;%1&apos;: saveConfig failed: %2 — layout save will skip plugin config</source>
        <translation>外掛程式「%1」：saveConfig 失敗：%2；儲存版面配置時將跳過外掛程式設定</translation>
    </message>
    <message>
        <location line="-400"/>
        <location line="+416"/>
        <source>Loader metadata rejected: %1</source>
        <translation>載入器中繼資料被拒絕：%1</translation>
    </message>
    <message>
        <location line="-372"/>
        <location line="+187"/>
        <location line="+8"/>
        <source>Import discarded</source>
        <translation>匯入已丟棄</translation>
    </message>
    <message>
        <location line="-190"/>
        <source>All %1 entries of &apos;%2&apos; failed to load:
%3</source>
        <translation>「%2」的全部 %1 個條目均載入失敗：
%3</translation>
    </message>
    <message>
        <location line="+50"/>
        <source>Cannot load &apos;%1&apos;: not a readable file.</source>
        <translation>無法載入「%1」：檔案不可讀。</translation>
    </message>
    <message>
        <location line="+146"/>
        <source>Plugin &apos;%1&apos;: start failed: %2</source>
        <translation>外掛程式「%1」：啟動失敗：%2</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>Plugin &apos;%1&apos;: derived-series replay failed: %2</source>
        <translation>外掛程式「%1」：衍生序列重播失敗：%2</translation>
    </message>
    <message>
        <location line="+218"/>
        <source>%1 loads failed</source>
        <translation>%1 項載入失敗</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Load failed</source>
        <translation>載入失敗</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>OK</source>
        <translation>確定</translation>
    </message>
</context>
<context>
    <name>PJ::FilterEditorPanel</name>
    <message>
        <location filename="../../pj_plotting/widget/src/FilterEditorPanel.cpp" line="+119"/>
        <location line="+348"/>
        <source>Apply</source>
        <translation>套用</translation>
    </message>
    <message>
        <location line="-344"/>
        <source>Close</source>
        <translation>關閉</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Warning: built-in filter definitions failed to load</source>
        <translation>警告：未能載入內建濾波器定義</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Copy parameters</source>
        <translation>複製參數</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Paste parameters</source>
        <translation>貼上參數</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Copy these parameters into all series</source>
        <translation>將這些參數複製到所有序列</translation>
    </message>
    <message>
        <location line="+95"/>
        <source>-- No Transform --</source>
        <translation>-- 無轉換 --</translation>
    </message>
    <message>
        <location line="+198"/>
        <source>Filter &apos;%1&apos; is not available</source>
        <translation>濾波器「%1」不可用</translation>
    </message>
    <message>
        <location line="+67"/>
        <source>Could not read filter parameters; using defaults</source>
        <translation>無法讀取濾波器參數；將使用預設值</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Pick a filter to copy</source>
        <translation>請選擇要複製的濾波器</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Filter copied</source>
        <translation>已複製濾波器</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Nothing to paste</source>
        <translation>沒有可貼上的內容</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Cannot paste filter &apos;%1&apos;</source>
        <translation>無法貼上濾波器「%1」</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Filter pasted</source>
        <translation>已貼上濾波器</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Pick a filter to copy to all series</source>
        <translation>請選擇要複製到所有序列的濾波器</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Copied to all %1 series</source>
        <translation>已複製到全部 %1 個序列</translation>
    </message>
    <message>
        <location line="+76"/>
        <location line="+43"/>
        <source>filtered</source>
        <translation>濾波結果</translation>
    </message>
    <message>
        <location line="+65"/>
        <source>Select at least one source curve</source>
        <translation>請至少選擇一條來源曲線</translation>
    </message>
    <message>
        <location line="+32"/>
        <source>remove %1: %2</source>
        <translation>移除 %1：%2</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Pick a filter to apply</source>
        <translation>請選擇要套用的濾波器</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>%1: filter &apos;%2&apos; is unavailable</source>
        <translation>%1：濾波器「%2」不可用</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>update %1: %2</source>
        <translation>更新 %1：%2</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>%1: %2</source>
        <translation>%1：%2</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>%1 filter(s) failed: %2</source>
        <translation>%1 個濾波器處理失敗：%2</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Nothing applied</source>
        <translation>未套用任何變更</translation>
    </message>
</context>
<context>
    <name>PJ::ImageLayer</name>
    <message>
        <location filename="../../pj_scene2D/widgets/src/layers/image_layer.cpp" line="+153"/>
        <source>Rectify (lens-undistort) the image using its camera calibration when a matching
CameraInfo is available. Turn off to show the raw image — e.g. when the stream is
already rectified and would otherwise be undistorted twice.</source>
        <translation>存在符合的 CameraInfo 時，使用相機校正參數校正影像（去除鏡頭畸變）。
關閉此選項可顯示原始影像；例如，影像串流已完成校正時，
應關閉此選項，以免重複去畸變。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Rectify</source>
        <translation>畸變校正</translation>
    </message>
</context>
<context>
    <name>PJ::LayerRowWidget</name>
    <message>
        <location filename="../../pj_widgets/src/LayerListView.cpp" line="+71"/>
        <source>Toggle layer visibility</source>
        <translation>顯示或隱藏圖層</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Remove this layer</source>
        <translation>移除此圖層</translation>
    </message>
</context>
<context>
    <name>PJ::LayoutImportBatch</name>
    <message>
        <location filename="../src/LayoutImportBatch.cpp" line="+144"/>
        <source>%1; the data source does not exist on disk</source>
        <translation>%1；磁碟上不存在此資料來源</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Layout&apos;s data source &apos;%1&apos; does not exist on disk and no provider could re-obtain it (%2).</source>
        <translation>版面配置的資料來源「%1」在磁碟上不存在，也沒有提供者能夠重新取得它（%2）。</translation>
    </message>
    <message>
        <location line="+49"/>
        <source>Layout source &apos;%1&apos; carries an invalid &lt;materialize&gt; record; falling back to the saved path.</source>
        <translation>版面配置資料來源「%1」包含無效的 &lt;materialize&gt; 記錄；將嘗試使用已儲存的路徑。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>invalid &lt;materialize&gt; record</source>
        <translation>無效的 &lt;materialize&gt; 記錄</translation>
    </message>
    <message>
        <location line="+48"/>
        <source>another PlotJuggler instance is currently downloading this request; wait for it to finish and load the layout again</source>
        <translation>另一個 PlotJuggler 執行個體正在下載此要求的資料；請等待下載完成後重新載入版面配置</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Layout source &apos;%1&apos;: another PlotJuggler instance is currently downloading this request; wait for it to finish and load the layout again.</source>
        <translation>版面配置資料來源「%1」：另一個 PlotJuggler 執行個體正在下載此要求的資料；請等待下載完成後重新載入版面配置。</translation>
    </message>
    <message>
        <location line="+24"/>
        <source>provider &apos;%1&apos; is unavailable: %2</source>
        <translation>提供者「%1」不可用：%2</translation>
    </message>
    <message>
        <location line="+4"/>
        <location line="+39"/>
        <source>Layout source &apos;%1&apos;: %2; falling back to the saved path.</source>
        <translation>版面配置資料來源「%1」：%2；將嘗試使用已儲存的路徑。</translation>
    </message>
    <message>
        <location line="-28"/>
        <source>provider returned no source identity</source>
        <translation>提供者未傳回資料來源識別</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Provider &apos;%1&apos; answered the query for layout source &apos;%2&apos; without a source identity.</source>
        <translation>提供者「%1」回應了版面配置資料來源「%2」的查詢，但未傳回資料來源識別。</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>provider &apos;%1&apos; could not resolve it: %2</source>
        <translation>提供者「%1」無法解析此資料來源：%2</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>no local path</source>
        <translation>沒有本機路徑</translation>
    </message>
    <message>
        <location line="+22"/>
        <source>descriptor refused by provider</source>
        <translation>提供者拒絕了描述資訊</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Provider &apos;%1&apos; refused the import descriptor for &apos;%2&apos;%3</source>
        <translation>提供者「%1」拒絕了「%2」的匯入描述資訊%3</translation>
    </message>
    <message>
        <location line="+39"/>
        <source>provider cache verdict is inconsistent</source>
        <translation>提供者傳回的快取狀態不一致</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Provider &apos;%1&apos; reports layout source &apos;%2&apos; as materialized, but no file exists there.</source>
        <translation>提供者「%1」報告版面配置資料來源「%2」已下載到本機，但對應檔案不存在。</translation>
    </message>
    <message>
        <location line="+7"/>
        <location line="+256"/>
        <source>untrusted import origin</source>
        <translation>不受信任的匯入來源</translation>
    </message>
    <message>
        <location line="-255"/>
        <source>Layout source &apos;%1&apos; requires confirmation of an untrusted origin; refused in non-interactive mode. Connect to this server once in the provider toolbox to trust it.</source>
        <translation>版面配置資料來源「%1」需要確認是否信任其來源；非互動模式下已拒絕匯入。請先在提供者工具箱中連線此伺服器並確認信任。</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>estimated size exceeds the transfer limit</source>
        <translation>預計大小超出傳輸限制</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Layout source &apos;%1&apos; estimates %2 bytes, above the configured limit of %3 bytes; refused in non-interactive mode.</source>
        <translation>版面配置資料來源「%1」的預計大小為 %2 位元組，超出了設定的 %3 位元組限制；非互動模式下已拒絕匯入。</translation>
    </message>
    <message>
        <location line="+82"/>
        <source>%1  (about %2)</source>
        <translation>%1  （約 %2）</translation>
    </message>
    <message>
        <location line="+104"/>
        <source>the loader rejected the file</source>
        <translation>載入器拒絕了此檔案</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>The loader rejected layout source &apos;%1&apos;.</source>
        <translation>載入器拒絕了版面配置資料來源「%1」。</translation>
    </message>
    <message>
        <location line="+30"/>
        <source>Cached copy of layout source &apos;%1&apos; failed to load%2; falling back to the provider.</source>
        <translation>版面配置資料來源「%1」的快取副本載入失敗%2；將嘗試從提供者重新取得。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source> and was removed</source>
        <translation>並已移除</translation>
    </message>
    <message>
        <location line="+28"/>
        <source>Layout source &apos;%1&apos; requires confirmation of an untrusted origin, which cannot be asked after the batch started. Connect to this server once in the provider toolbox to trust it.</source>
        <translation>版面配置資料來源「%1」需要確認是否信任其來源，但批次開始後無法再要求確認。請先在提供者工具箱中連線此伺服器並確認信任。</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>provider session unavailable</source>
        <translation>提供者工作階段不可用</translation>
    </message>
    <message>
        <location line="+24"/>
        <source>Import of layout source &apos;%1&apos; could not start: %2</source>
        <translation>無法開始匯入版面配置資料來源「%1」：%2</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>Layout source &apos;%1&apos; imported as data only (no re-importable source record was attached).</source>
        <translation>版面配置資料來源「%1」僅匯入了資料，未附帶可用於再次匯入的資料來源記錄。</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Import of layout source &apos;%1&apos; was cancelled.</source>
        <translation>已取消匯入版面配置資料來源「%1」。</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Import of layout source &apos;%1&apos; failed: %2</source>
        <translation>匯入版面配置資料來源「%1」失敗：%2</translation>
    </message>
    <message>
        <location line="+81"/>
        <source>the stock load failed</source>
        <translation>常規載入失敗</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Loading layout source &apos;%1&apos; failed.</source>
        <translation>載入版面配置資料來源「%1」失敗。</translation>
    </message>
    <message>
        <location line="+77"/>
        <source>The cancelled layout import was removed, but the previous workspace could not be restored exactly.</source>
        <translation>已移除取消的版面配置匯入，但無法精確還原之前的工作區。</translation>
    </message>
</context>
<context>
    <name>PJ::LeftPanel</name>
    <message>
        <location filename="../src/ui/LeftPanel.cpp" line="+90"/>
        <source>(no recent layouts)</source>
        <translation>（沒有最近使用的版面配置）</translation>
    </message>
    <message>
        <location line="+4"/>
        <location line="+41"/>
        <source>Layouts</source>
        <translation>版面配置</translation>
    </message>
    <message>
        <location line="-34"/>
        <source>Stored in this browser; no source file bytes are retained.</source>
        <translation>儲存在目前瀏覽器中；不會保留來源檔案內容。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Clear recent layouts</source>
        <translation>清除最近使用的版面配置</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>(no recent files or layouts)</source>
        <translation>（沒有最近使用的檔案或版面配置）</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Files</source>
        <translation>檔案</translation>
    </message>
    <message>
        <location line="+180"/>
        <source>Resume streaming</source>
        <translation>繼續接收串流資料</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Pause streaming</source>
        <translation>暫停接收串流資料</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Stop recording</source>
        <translation>停止錄製</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Record the subscribed topics of every active stream, one MCAP file per stream</source>
        <translation>錄製每個作用中的資料串流中已訂閱的主題，每個資料串流儲存為一個 MCAP 檔案</translation>
    </message>
    <message>
        <location line="+253"/>
        <source>(no cloud plugins)</source>
        <translation>（沒有雲端外掛程式）</translation>
    </message>
</context>
<context>
    <name>PJ::MainWindow</name>
    <message>
        <location filename="../src/MainWindow.cpp" line="+338"/>
        <source>PlotJuggler 4 Layout (*.pj4.xml)</source>
        <translation>PlotJuggler 4 版面配置 (*.pj4.xml)</translation>
    </message>
    <message>
        <location line="+392"/>
        <source>Open Data File...</source>
        <translation>開啟資料檔案…</translation>
    </message>
    <message>
        <location line="+7"/>
        <location line="+7"/>
        <source>Load Layout...</source>
        <translation>載入版面配置…</translation>
    </message>
    <message>
        <location line="-6"/>
        <location line="+8"/>
        <source>Save Layout...</source>
        <translation>儲存版面配置…</translation>
    </message>
    <message>
        <location line="-5"/>
        <source>Preferences...</source>
        <translation>偏好設定…</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Save Layout with Sources...</source>
        <translation>儲存版面配置及資料來源參照…</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>About PlotJuggler...</source>
        <translation>關於 PlotJuggler…</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Check for Updates...</source>
        <translation>檢查更新…</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Documentation</source>
        <translation>使用文件</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Report a Localization Issue</source>
        <translation>回報翻譯問題</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Report an Upstream Issue</source>
        <translation>回報上游問題</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Installed Extensions</source>
        <translation>已安裝的擴充功能</translation>
    </message>
    <message>
        <location line="+44"/>
        <source>A plugin failed to load.</source>
        <translation>有一個外掛程式載入失敗。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Plugin &apos;%1&apos; failed to load.</source>
        <translation>外掛程式「%1」載入失敗。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Details are in the notifications.</source>
        <translation>詳細資料請查看通知。</translation>
    </message>
    <message>
        <location line="+51"/>
        <source>This object topic cannot be displayed (type %1).</source>
        <translation>無法顯示此物件主題（型別為 %1）。</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>This object topic cannot be displayed in a 3D view (type %1). The 3D view requires a registered parser that emits one of its supported canonical objects (PointCloud, CompressedPointCloud, OccupancyGrid, SceneEntities, or FrameTransforms).</source>
        <translation>無法在三維檢視中顯示此物件主題（型別為 %1）。三維檢視需要已註冊的解析器將其轉換為支援的標準物件型別：PointCloud、CompressedPointCloud、OccupancyGrid、SceneEntities 或 FrameTransforms。</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>This object topic cannot be displayed in a 2D view (type %1). Typically this means the source did not register a parser for the topic, or the type is not yet supported by the built-in viewer.</source>
        <translation>無法在二維檢視中顯示此物件主題（型別為 %1）。通常是因為資料來源未為該主題註冊解析器，或者內建查看器尚不支援此型別。</translation>
    </message>
    <message>
        <location line="+169"/>
        <location line="+2129"/>
        <location line="+89"/>
        <source>dataset removed</source>
        <translation>資料集已移除</translation>
    </message>
    <message>
        <location line="-1823"/>
        <source>Start Streaming</source>
        <translation>開始接收串流資料</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>The stream could not be started:

%1</source>
        <translation>無法啟動資料串流：

%1</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Streaming</source>
        <translation>串流資料</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>The stream failed:

%1</source>
        <translation>資料串流發生錯誤：

%1</translation>
    </message>
    <message>
        <location line="+396"/>
        <source>Stop loading…</source>
        <translation>停止載入…</translation>
    </message>
    <message>
        <location line="+70"/>
        <source>Stop loading?</source>
        <translation>停止載入？</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>This data is still loading. Keep what has loaded so far, remove all of it, or keep loading?</source>
        <translation>資料仍在載入中。要保留已載入的資料、全部移除，還是繼續載入？</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Remove All</source>
        <translation>全部移除</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Stop and Keep</source>
        <translation>停止並保留</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+1239"/>
        <location line="+162"/>
        <location line="+1762"/>
        <location line="+250"/>
        <location line="+3140"/>
        <source>Cancel</source>
        <translation>取消</translation>
    </message>
    <message>
        <location line="-6463"/>
        <source>Undo</source>
        <translation>復原</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Redo</source>
        <translation>重做</translation>
    </message>
    <message>
        <location line="+77"/>
        <source>No widget selected</source>
        <translation>未選擇檢視元件</translation>
    </message>
    <message>
        <location line="+257"/>
        <source>Loaded test sin/cos data</source>
        <translation>已載入正弦/餘弦測試資料</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Browser source state is unavailable.</source>
        <translation>瀏覽器資料來源狀態不可用。</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Open a browser data source before saving a source-bound layout.</source>
        <translation>儲存繫結資料來源的版面配置之前，請先在瀏覽器中開啟一個資料來源。</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Every loaded dataset must be backed by a browser-selected file.</source>
        <translation>每個已載入的資料集都必須來自瀏覽器中選擇的檔案。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>A loaded browser source can no longer be identified.</source>
        <translation>無法再識別某個已載入的瀏覽器資料來源。</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>A browser source no longer has its complete original dataset set.</source>
        <translation>某個瀏覽器資料來源的原始資料集已不完整。</translation>
    </message>
    <message>
        <location line="+25"/>
        <source>A browser source has no usable filename.</source>
        <translation>某個瀏覽器資料來源沒有可用的檔案名稱。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>A browser source no longer has its staged content fingerprint.</source>
        <translation>某個瀏覽器資料來源的暫存內容指紋已遺失。</translation>
    </message>
    <message>
        <location line="+70"/>
        <location line="+2121"/>
        <source>The layout still contains an ephemeral browser path and was not downloaded.</source>
        <translation>版面配置仍包含暫時瀏覽器路徑，因此未下載。</translation>
    </message>
    <message>
        <location line="-1995"/>
        <source>Remove all Datasets</source>
        <translation>移除全部資料集</translation>
    </message>
    <message>
        <location line="+192"/>
        <location line="+18"/>
        <source>Marketplace</source>
        <translation>擴充功能市場</translation>
    </message>
    <message>
        <location line="+245"/>
        <source>The source was reloaded, but some workspace bindings could not be mapped to its new datasets.</source>
        <translation>已重新載入資料來源，但部分工作區繫結無法映射到新的資料集。</translation>
    </message>
    <message numerus="yes">
        <location line="+49"/>
        <source>%n derived series</source>
        <translation>
            <numerusform>%n 個衍生序列</numerusform>
        </translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Delete derived series?</source>
        <translation>刪除衍生序列？</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>These derived series depend on what you are deleting and will also be removed:

• %1</source>
        <translation>以下衍生序列依賴於將要刪除的內容，也會一並移除：

• %1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Delete</source>
        <translation>刪除</translation>
    </message>
    <message>
        <location line="+156"/>
        <source>Are you sure you want to remove &apos;%1&apos; and its data?</source>
        <translation>確定要移除「%1」及其資料嗎？</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Are you sure you want to remove these %1 datasets and their data?</source>
        <translation>確定要移除這 %1 個資料集及其資料嗎？</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Remove dataset</source>
        <translation>移除資料集</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Remove datasets</source>
        <translation>移除資料集</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Remove</source>
        <translation>移除</translation>
    </message>
    <message>
        <location line="+109"/>
        <source>New release available: &lt;b&gt;%1&lt;/b&gt;</source>
        <translation>有新版本可用：&lt;b&gt;%1&lt;/b&gt;</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Update with &lt;code&gt;sudo apt update &amp;amp;&amp;amp; sudo apt upgrade&lt;/code&gt;</source>
        <translation>使用以下指令更新：&lt;code&gt;sudo apt update &amp;amp;&amp;amp; sudo apt upgrade&lt;/code&gt;</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Get it, and future releases, through apt:&lt;br&gt;&lt;code&gt;curl -fsSL https://apt.plotjuggler.io/pj4_install.sh | sudo sh&lt;/code&gt;</source>
        <translation>透過 apt 取得目前及後續版本：&lt;br&gt;&lt;code&gt;curl -fsSL https://apt.plotjuggler.io/pj4_install.sh | sudo sh&lt;/code&gt;</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>&lt;a href=&quot;pj-update:maintenance-tool&quot;&gt;Update now&lt;/a&gt; (PlotJuggler will close)</source>
        <translation>&lt;a href=&quot;pj-update:maintenance-tool&quot;&gt;立即更新&lt;/a&gt;（PlotJuggler 將關閉）</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>&lt;a href=&quot;%1&quot;&gt;View on GitHub&lt;/a&gt;</source>
        <translation>&lt;a href=&quot;%1&quot;&gt;在 GitHub 上查看&lt;/a&gt;</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&lt;a href=&quot;%1&quot;&gt;Release notes&lt;/a&gt;</source>
        <translation>&lt;a href=&quot;%1&quot;&gt;版本說明&lt;/a&gt;</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>PlotJuggler is up to date.</source>
        <translation>PlotJuggler 已是最新版本。</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Could not check for updates. Please try again later.</source>
        <translation>無法檢查更新，請稍後重試。</translation>
    </message>
    <message>
        <location line="+22"/>
        <source>Could not start the PlotJuggler maintenance tool.</source>
        <translation>無法啟動 PlotJuggler 維護工具。</translation>
    </message>
    <message>
        <location line="+332"/>
        <source>Close the open panel before applying a filter</source>
        <translation>套用濾波器之前，請先關閉目前面板</translation>
    </message>
    <message>
        <location line="+404"/>
        <source>Nothing to record: start a streaming source first.</source>
        <translation>沒有可錄製的內容：請先啟動一個串流資料來源。</translation>
    </message>
    <message numerus="yes">
        <location line="+1"/>
        <source>Nothing to record: %n active source(s) write decoded samples directly, which cannot be recorded.</source>
        <translation>
            <numerusform>沒有可錄製的內容：%n 個作用中的資料來源直接寫入解碼後的取樣，無法錄製。</numerusform>
        </translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Recording could not start: %1</source>
        <translation>無法開始錄製：%1</translation>
    </message>
    <message numerus="yes">
        <location line="+6"/>
        <source>%n source(s) write decoded samples directly and are not recorded: %1</source>
        <translation>
            <numerusform>%n 個資料來源直接寫入解碼後的取樣，未參與錄製：%1</numerusform>
        </translation>
    </message>
    <message>
        <location line="+10"/>
        <source>0:00 | %1</source>
        <translation>0:00 | %1</translation>
    </message>
    <message>
        <location line="+24"/>
        <source>Recording saved to %1</source>
        <translation>錄製已儲存到 %1</translation>
    </message>
    <message numerus="yes">
        <location line="+1"/>
        <source>%n recording(s) saved to %1</source>
        <translation>
            <numerusform>%n 個錄製檔案已儲存到 %1</numerusform>
        </translation>
    </message>
    <message>
        <location line="+10"/>
        <source>%1 (%2)</source>
        <translation>%1（%2）</translation>
    </message>
    <message numerus="yes">
        <location line="+2"/>
        <source>%n of %1 recording(s) had problems: %2</source>
        <translation>
            <numerusform>%1 個錄製檔案中有 %n 個出現問題：%2</numerusform>
        </translation>
    </message>
    <message>
        <location line="+5"/>
        <source> An unfinalized file still opens; run &apos;mcap recover&apos; to rebuild its index.</source>
        <translation> 未正常結束的檔案仍可開啟；執行「mcap recover」可重建索引。</translation>
    </message>
    <message numerus="yes">
        <location line="+5"/>
        <source> (%n message(s) dropped: the disk could not keep up)</source>
        <translation>
            <numerusform>（已丟棄 %n 條訊息：磁碟寫入速度不足）</numerusform>
        </translation>
    </message>
    <message numerus="yes">
        <location line="+4"/>
        <source> (%n message(s) could not be recorded)</source>
        <translation>
            <numerusform>（%n 條訊息無法錄製）</numerusform>
        </translation>
    </message>
    <message>
        <location line="+7"/>
        <source>%1:%2 | %3</source>
        <translation>%1:%2 | %3</translation>
    </message>
    <message>
        <location line="+7"/>
        <source> | %1 dropped</source>
        <translation> | 已丟棄 %1 條</translation>
    </message>
    <message>
        <location line="+212"/>
        <source>application shutdown</source>
        <translation>應用程式關閉</translation>
    </message>
    <message>
        <location line="+104"/>
        <location line="+448"/>
        <location line="+103"/>
        <location line="+705"/>
        <location line="+9"/>
        <location line="+387"/>
        <location line="+346"/>
        <source>Load Layout</source>
        <translation>載入版面配置</translation>
    </message>
    <message>
        <location line="-1983"/>
        <location line="+25"/>
        <location line="+2049"/>
        <location line="+7"/>
        <location line="+5"/>
        <source>Save Layout</source>
        <translation>儲存版面配置</translation>
    </message>
    <message>
        <location line="-2079"/>
        <source>Requested layout download: %1</source>
        <translation>已要求下載版面配置：%1</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Bind to this data source</source>
        <translation>繫結到此資料來源</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Save Layout with Sources</source>
        <translation>儲存版面配置及資料來源參照</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Requested source-bound layout download: %1</source>
        <translation>已要求下載繫結資料來源的版面配置：%1</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>This browser no longer has that recent layout recipe.</source>
        <translation>此瀏覽器中已沒有該最近使用的版面配置設定。</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Layout file no longer exists: %1</source>
        <translation>版面配置檔案已不存在：%1</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>(no extensions installed)</source>
        <translation>（未安裝擴充功能）</translation>
    </message>
    <message>
        <location line="+141"/>
        <source>(no toolboxes available)</source>
        <translation>（沒有可用的工具箱）</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Cannot open &apos;%1&apos; for reading.</source>
        <translation>無法開啟「%1」進行讀取。</translation>
    </message>
    <message>
        <location line="+10"/>
        <location line="+244"/>
        <source>&apos;%1&apos; is not a valid PJ4 layout: %2 (line %3, col %4)</source>
        <translation>「%1」不是有效的 PJ4 版面配置：%2（第 %3 行，第 %4 欄）</translation>
    </message>
    <message>
        <location line="-223"/>
        <location line="+259"/>
        <source>Layout &apos;%1&apos; was saved by a newer PJ4 (pj4_version=%2 &gt; %3); loading best-effort.</source>
        <translation>版面配置「%1」由更高版本的 PJ4 儲存（pj4_version=%2 &gt; %3）；將盡可能載入。</translation>
    </message>
    <message>
        <location line="-171"/>
        <source>Layout&apos;s data source &apos;%1&apos; does not exist on disk; applying to current data.</source>
        <translation>版面配置的資料來源「%1」在磁碟上不存在；將套用到目前資料。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>does not exist on disk</source>
        <translation>在磁碟上不存在</translation>
    </message>
    <message numerus="yes">
        <location line="+30"/>
        <source>This layout was saved with %n data source(s):

%1</source>
        <translation>
            <numerusform>此版面配置儲存了 %n 個資料來源的參照：

%1</numerusform>
        </translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Reload source file</source>
        <translation>重新載入來源檔案</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Load Layout only</source>
        <translation>僅載入版面配置</translation>
    </message>
    <message>
        <location line="+81"/>
        <source>No data is loaded, and the layout&apos;s data sources could not be restored:

%1</source>
        <translation>目前沒有載入資料，且無法還原版面配置的資料來源：

%1</translation>
    </message>
    <message>
        <location line="+91"/>
        <location line="+36"/>
        <location line="+12"/>
        <location line="+12"/>
        <location line="+121"/>
        <location line="+90"/>
        <location line="+10"/>
        <location line="+12"/>
        <location line="+187"/>
        <source>Load source-bound layout</source>
        <translation>載入繫結資料來源的版面配置</translation>
    </message>
    <message>
        <location line="-479"/>
        <source>This layout references cloud-materialized data sources, which are unsupported in the browser. Open it in the desktop PlotJuggler instead.</source>
        <translation>此版面配置參照了從雲端下載的資料來源，瀏覽器暫不支援。請使用桌面版 PlotJuggler 開啟。</translation>
    </message>
    <message>
        <location line="+35"/>
        <source>The layout does not uniquely identify every saved data source.</source>
        <translation>此版面配置無法唯一識別每個已儲存的資料來源。</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>This older layout contains more than one source named &apos;%1&apos;, but no content fingerprints to tell them apart safely. Open the sources separately and use a newer source-bound layout.</source>
        <translation>此舊版版面配置包含多個名為「%1」的資料來源，但缺少內容指紋，無法安全區分。請分別開啟這些資料來源，並使用新版繫結資料來源的版面配置。</translation>
    </message>
    <message>
        <location line="+16"/>
        <location line="+251"/>
        <source>%1 (plugin: %2)</source>
        <translation>%1（外掛程式：%2）</translation>
    </message>
    <message>
        <location line="-248"/>
        <source>This layout was saved with data source &apos;%1&apos;. Reselect that file to reload it, or apply the layout to compatible data already open in this page.</source>
        <translation>此版面配置儲存了資料來源「%1」的參照。請重新選擇該檔案以載入資料，或將版面配置套用到目前頁面中已開啟的相容資料。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>This layout was saved with %1 data sources. Select source 1 of %1: &apos;%2&apos; for saved slot &apos;%3&apos;. Every file will be staged before any import begins.</source>
        <translation>此版面配置儲存了 %1 個資料來源的參照。請選擇第 1 個資料來源（共 %1 個）：「%2」，對應儲存的槽位「%3」。所有檔案暫存完成後才會開始匯入。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Reselect source</source>
        <translation>重新選擇資料來源</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Select source 1 of %1</source>
        <translation>選擇資料來源 1 / %1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Apply to current data</source>
        <translation>套用到目前資料</translation>
    </message>
    <message>
        <location line="+104"/>
        <source>The currently open browser data does not uniquely match every saved source.</source>
        <translation>瀏覽器中目前開啟的資料無法與每個已儲存的資料來源一一對應。</translation>
    </message>
    <message>
        <location line="+100"/>
        <source>Select &apos;%1&apos; to replay this layout (selected &apos;%2&apos;).</source>
        <translation>請選擇「%1」以重播此版面配置（目前選擇的是「%2」）。</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>The selected &apos;%1&apos; is not the file saved for source %2 of %3 (&apos;%4&apos;). Select the original file for that saved slot.</source>
        <translation>選取的「%1」不是第 %2 個資料來源（共 %3 個，「%4」）所儲存的檔案。請選擇該槽位對應的原始檔案。</translation>
    </message>
    <message>
        <location line="+25"/>
        <source>Staged %1 of %2 data sources. Select source %3 of %2: &apos;%4&apos; for saved slot &apos;%5&apos;. No import has started yet.</source>
        <translation>已暫存 %1 個資料來源，共 %2 個。請選擇第 %3 個資料來源（共 %2 個）：「%4」，對應儲存的槽位「%5」。尚未開始匯入。</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Select source %1 of %2</source>
        <translation>選擇資料來源 %1 / %2</translation>
    </message>
    <message>
        <location line="+66"/>
        <source>A staged source could not be queued for import.</source>
        <translation>某個已暫存的資料來源無法加入匯入佇列。</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>One or more selected sources closed without completing their import.</source>
        <translation>一個或多個選取的資料來源在匯入完成前已關閉。</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Source &apos;%1&apos; produced %2 dataset(s); the layout requires exactly %3.</source>
        <translation>資料來源「%1」產生了 %2 個資料集；此版面配置要求恰好 %3 個。</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Source &apos;%1&apos; did not reproduce the saved fan-out dataset order and names.</source>
        <translation>資料來源「%1」未能產生與已儲存的分割資料集相同的順序和名稱。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>The saved Source Timeline contains duplicate track positions.</source>
        <translation>儲存的資料來源時間軸包含重複的軌道位置。</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>A saved Source Timeline offset is outside the supported range.</source>
        <translation>儲存的資料來源時間軸偏移量超出支援範圍。</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>A saved Source Timeline offset is outside the selected dataset&apos;s supported range.</source>
        <translation>儲存的資料來源時間軸偏移量超出所選資料集的支援範圍。</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>The saved Source Timeline contains invalid track positions.</source>
        <translation>儲存的資料來源時間軸包含無效的軌道位置。</translation>
    </message>
    <message>
        <location line="+57"/>
        <source>The failed source replay was removed, but the previous workspace could not be restored exactly.</source>
        <translation>已移除失敗的資料來源重播結果，但無法精確還原之前的工作區。</translation>
    </message>
    <message>
        <location line="+100"/>
        <location line="+53"/>
        <source>No data is loaded. Open a data source before applying this layout.</source>
        <translation>目前沒有載入資料。請先開啟資料來源，再套用此版面配置。</translation>
    </message>
    <message>
        <location line="-43"/>
        <source>Layout was parsed but could not be applied to the currently loaded data. Open matching data sources and try again.</source>
        <translation>版面配置已解析，但無法套用到目前載入的資料。請開啟符合的資料來源後重試。</translation>
    </message>
    <message>
        <location line="+23"/>
        <location line="+110"/>
        <source>Loaded layout: %1</source>
        <translation>已載入版面配置：%1</translation>
    </message>
    <message>
        <location line="-55"/>
        <source>Layout was parsed but could not be applied. If a data source was reloaded, it is still loaded.</source>
        <translation>版面配置已解析，但無法套用。若已重新載入資料來源，該資料仍然保留。</translation>
    </message>
    <message>
        <location line="+101"/>
        <source>Layout was parsed but could not be applied.</source>
        <translation>版面配置已解析，但無法套用。</translation>
    </message>
    <message numerus="yes">
        <location line="+239"/>
        <source>%n layout reference(s) could not be bound after the import: %1</source>
        <translation>
            <numerusform>匯入後無法繫結 %n 個版面配置參照：%1</numerusform>
        </translation>
    </message>
    <message numerus="yes">
        <location line="+29"/>
        <source>%n scene layer(s) could not be rebound after progressive load.</source>
        <translation>
            <numerusform>漸進式載入後無法重新繫結 %n 個場景圖層。</numerusform>
        </translation>
    </message>
    <message>
        <location line="+28"/>
        <source>A saved data processor could not be restored; the previous workspace was restored.</source>
        <translation>無法還原某個已儲存的資料處理器；已還原之前的工作區。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>A saved data processor could not be restored, and the previous workspace could not be fully restored against the reloaded data. The partial layout was kept as the new undo baseline.</source>
        <translation>無法還原某個已儲存的資料處理器，也無法基於重新載入的資料完整還原之前的工作區。已保留部分還原的版面配置，作為新的復原基線。</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>A saved scene element was invalid; the previous workspace was restored.</source>
        <translation>某個已儲存的場景元素無效；已還原之前的工作區。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>A saved scene element was invalid, and the previous workspace could not be fully restored against the reloaded data. The partial layout was kept as the new undo baseline.</source>
        <translation>某個已儲存的場景元素無效，且無法基於重新載入的資料完整還原之前的工作區。已保留部分還原的版面配置，作為新的復原基線。</translation>
    </message>
    <message>
        <location line="+183"/>
        <source>Layout import was cancelled; the previous workspace was restored.</source>
        <translation>版面配置匯入已取消；已還原之前的工作區。</translation>
    </message>
    <message numerus="yes">
        <location line="+58"/>
        <source>This layout asks to download %n data source(s) from a cloud provider:

%1</source>
        <translation>
            <numerusform>此版面配置要求從雲端提供者下載 %n 個資料來源：

%1</numerusform>
        </translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Trust and import</source>
        <translation>信任並匯入</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Skip these sources</source>
        <translation>跳過這些資料來源</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Cancel layout load</source>
        <translation>取消載入版面配置</translation>
    </message>
    <message>
        <location line="+85"/>
        <source>Cannot open &apos;%1&apos; for writing.</source>
        <translation>無法開啟「%1」進行寫入。</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Failed to write layout to &apos;%1&apos;: %2</source>
        <translation>無法將版面配置寫入「%1」：%2</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Failed to finalize layout &apos;%1&apos;: %2</source>
        <translation>無法完成版面配置「%1」的儲存：%2</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Saved layout: %1</source>
        <translation>已儲存版面配置：%1</translation>
    </message>
    <message>
        <location line="+184"/>
        <source>invalid input dataset id</source>
        <translation>輸入資料集 ID 無效</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>ambiguous input dataset path</source>
        <translation>輸入資料集路徑存在歧義</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>input dataset path is not loaded</source>
        <translation>輸入資料集路徑尚未載入</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>invalid input column</source>
        <translation>輸入欄無效</translation>
    </message>
    <message>
        <location line="+20"/>
        <location line="+109"/>
        <source>Could not restore transform &apos;%1&apos;: %2</source>
        <translation>無法還原轉換「%1」：%2</translation>
    </message>
    <message>
        <location line="-39"/>
        <source>Layout filter on &apos;%1/%2&apos; has no matching data; skipping.</source>
        <translation>版面配置中「%1/%2」的濾波器沒有符合的資料；已跳過。</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Layout filter &apos;%1&apos; is unknown to this PlotJuggler; skipping.</source>
        <translation>目前 PlotJuggler 不識別版面配置中的濾波器「%1」；已跳過。</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Could not restore filter &apos;%1&apos;: %2</source>
        <translation>無法還原濾波器「%1」：%2</translation>
    </message>
    <message>
        <location line="+75"/>
        <source>Cannot undo: protected outputs would lose an input this step removes: %1</source>
        <translation>無法復原：此步驟會移除受保護輸出所依賴的輸入：%1</translation>
    </message>
    <message>
        <location line="+101"/>
        <source>ambiguous dataset identity</source>
        <translation>資料集識別存在歧義</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>dataset is not loaded</source>
        <translation>資料集尚未載入</translation>
    </message>
    <message>
        <location line="+28"/>
        <location line="+6"/>
        <source>Could not restore marker generator &apos;%1&apos;: %2</source>
        <translation>無法還原標記產生器「%1」：%2</translation>
    </message>
    <message>
        <location line="+381"/>
        <location line="+64"/>
        <source>The saved per-source time offsets could not be applied.</source>
        <translation>無法套用已儲存的各資料來源時間偏移。</translation>
    </message>
    <message numerus="yes">
        <location line="-46"/>
        <source>%n curve(s) have no matching data: %1</source>
        <translation>
            <numerusform>%n 條曲線沒有符合的資料：%1</numerusform>
        </translation>
    </message>
    <message numerus="yes">
        <location line="+30"/>
        <source>%n layout curve(s) could not be bound: %1</source>
        <translation>
            <numerusform>%n 條版面配置曲線無法繫結：%1</numerusform>
        </translation>
    </message>
    <message>
        <location line="+29"/>
        <source>A 2D/3D scene could not restore its layers (the element is named in the log).</source>
        <translation>某個二維/三維場景無法還原圖層（記錄檔中已標明對應元素）。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Scene layers have no matching data: %1</source>
        <translation>場景圖層沒有符合的資料：%1</translation>
    </message>
    <message numerus="yes">
        <location line="+6"/>
        <source>%n scene layer(s) could not be rebound and were omitted.</source>
        <translation>
            <numerusform>%n 個場景圖層無法重新繫結，已省略。</numerusform>
        </translation>
    </message>
    <message numerus="yes">
        <location line="+8"/>
        <source>%n scene layer(s) are not yet bound.</source>
        <translation>
            <numerusform>%n 個場景圖層尚未繫結。</numerusform>
        </translation>
    </message>
    <message>
        <location line="+121"/>
        <source>Unable to restore undo state</source>
        <translation>無法還原復原狀態</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Unable to restore redo state</source>
        <translation>無法還原重做狀態</translation>
    </message>
    <message numerus="yes">
        <location line="+581"/>
        <source>The layout references %n curve(s) not present in the current data:</source>
        <translation>
            <numerusform>此版面配置參照了目前資料中不存在的 %n 條曲線：</numerusform>
        </translation>
    </message>
    <message numerus="yes">
        <location line="+7"/>
        <source>  … and %n more
</source>
        <translation>
            <numerusform>  …以及另外 %n 條
</numerusform>
        </translation>
    </message>
    <message>
        <location line="+4"/>
        <source>The layout&apos;s data sources could not be restored:</source>
        <translation>無法還原此版面配置的資料來源：</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Choose how to handle them:</source>
        <translation>請選擇處理方式：</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Missing curves</source>
        <translation>缺失的曲線</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Remove from plots</source>
        <translation>從圖表中移除</translation>
    </message>
    <message>
        <location line="+39"/>
        <source>No &lt;root&gt; element at the top of the layout.</source>
        <translation>版面配置頂層缺少 &lt;root&gt; 元素。</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>No &lt;tabbed_widget&gt; element in the layout.</source>
        <translation>版面配置中缺少 &lt;tabbed_widget&gt; 元素。</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>The plot tabs could not be reconstructed from the layout.</source>
        <translation>無法從版面配置重建圖表分頁。</translation>
    </message>
    <message>
        <location line="+230"/>
        <source>Link X axis</source>
        <translation>聯動 X 軸</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Zoom Out All</source>
        <translation>縮放至全部資料</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Show/Hide the grid</source>
        <translation>顯示或隱藏網格</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Cycle TimeTracker display: line only / line + value / line + value + name</source>
        <translation>切換時間游標顯示：僅游標線 / 游標線和數值 / 游標線、數值和名稱</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Legend position — left-click walks TR → TL → BL → BR, then unchecks at TR before the next cycle. Right-click toggles show/hide at the current corner.</source>
        <translation>圖例位置：左鍵依次切換右上 → 左上 → 左下 → 右下，然後在右上角關閉顯示，再開始下一輪。右鍵切換目前角落圖例的顯示或隱藏。</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Show point in plot</source>
        <translation>顯示圖表中的資料點</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Keep aspect ratio of XY plots (1:1)</source>
        <translation>保持 XY 圖表的縱橫比為 1:1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Show data point markers on curves</source>
        <translation>顯示曲線上的資料點標記</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Drop a blue reference line at the playback position; values render as delta from there</source>
        <translation>在播放位置新增藍色參考線；數值顯示為相對於該位置的差值</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Use time offset: show time relative to each dataset&apos;s start (axis begins at 0) instead of absolute time</source>
        <translation>使用時間偏移：顯示相對於各資料集起點的時間（橫軸從 0 開始），而非絕對時間</translation>
    </message>
    <message>
        <location line="+138"/>
        <source>Align sources: line every source&apos;s start up at the earliest start</source>
        <translation>對齊資料來源：將各資料來源的起點對齊到最早的起點</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Align sources: line every source&apos;s end up at the latest end</source>
        <translation>對齊資料來源：將各資料來源的終點對齊到最晚的終點</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Zoom out to fit all sources</source>
        <translation>縮放以顯示全部資料來源</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Snap to neighbouring dataset edges while dragging</source>
        <translation>拖曳時吸附到相鄰資料集的邊界</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Reset all timeline changes</source>
        <translation>重設時間軸的全部變更</translation>
    </message>
    <message>
        <location line="+98"/>
        <source>Curve Width</source>
        <translation>曲線寬度</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Line width 1.0</source>
        <translation>線寬 1.0</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Line width 1.5</source>
        <translation>線寬 1.5</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Line width 2.0</source>
        <translation>線寬 2.0</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Line width 3.0</source>
        <translation>線寬 3.0</translation>
    </message>
    <message>
        <location line="+29"/>
        <source>Curve Style</source>
        <translation>曲線樣式</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Lines</source>
        <translation>線條</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Dots</source>
        <translation>散點</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Lines and Dots</source>
        <translation>線條和散點</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Sticks</source>
        <translation>棒狀</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Steps (pre)</source>
        <translation>階梯（前置）</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Steps (post)</source>
        <translation>階梯（後置）</translation>
    </message>
    <message>
        <location line="+423"/>
        <source>Cancel download?</source>
        <translation>取消下載？</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>A download is in progress. Cancel it and close?</source>
        <translation>下載正在進行中。是否取消下載並關閉？</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Cancel download &amp;&amp; close</source>
        <translation>取消下載並關閉</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Keep downloading</source>
        <translation>繼續下載</translation>
    </message>
    <message>
        <location line="+297"/>
        <source>Failed to publish toolbox services for &apos;%1&apos;: %2</source>
        <translation>無法為「%1」發佈工具箱服務：%2</translation>
    </message>
    <message>
        <location line="+39"/>
        <source>Failed to publish data-processor services for &apos;%1&apos;: %2</source>
        <translation>無法為「%1」發佈資料處理器服務：%2</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Failed to publish the source-promotion service for &apos;%1&apos;: %2</source>
        <translation>無法為「%1」發佈資料來源持久化服務：%2</translation>
    </message>
    <message>
        <location line="+25"/>
        <source>Failed to publish the playback service for &apos;%1&apos;: %2</source>
        <translation>無法為「%1」發佈播放服務：%2</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Failed to publish the viewport service for &apos;%1&apos;: %2</source>
        <translation>無法為「%1」發佈檢視區域服務：%2</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Failed to publish the plot-tab service for &apos;%1&apos;: %2</source>
        <translation>無法為「%1」發佈圖表分頁服務：%2</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Toolbox</source>
        <translation>工具箱</translation>
    </message>
    <message>
        <location line="+74"/>
        <source>Toolbox &apos;%1&apos; not found in catalog</source>
        <translation>目錄中未找到工具箱「%1」</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Failed to bind toolbox &apos;%1&apos;: %2</source>
        <translation>無法繫結工具箱「%1」：%2</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Toolbox &apos;%1&apos; returned no dialog</source>
        <translation>工具箱「%1」未傳回對話方塊</translation>
    </message>
    <message>
        <location line="+32"/>
        <source>Failed to build the panel UI for &apos;%1&apos;</source>
        <translation>無法建立「%1」的面板介面</translation>
    </message>
    <message>
        <location line="+66"/>
        <source>Cannot show &apos;%1&apos;: another panel is already open</source>
        <translation>無法顯示「%1」：已有另一個面板開啟</translation>
    </message>
    <message>
        <location line="+133"/>
        <source>Layout restore kept the current pinned panels: &apos;%1&apos; has a job still running.</source>
        <translation>還原版面配置時保留了目前固定的面板：「%1」仍有工作在執行。</translation>
    </message>
</context>
<context>
    <name>PJ::MarkerTimeline</name>
    <message>
        <location filename="../../pj_widgets/src/MarkerTimeline.cpp" line="+354"/>
        <source>Delete marker</source>
        <translation>刪除標記</translation>
    </message>
</context>
<context>
    <name>PJ::MarketplaceCatalog</name>
    <message>
        <location filename="../../pj_marketplace/include/pj_marketplace/marketplace_text.hpp" line="+17"/>
        <source>Arrow IPC Parser</source>
        <translation>Arrow IPC 解析器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Message parser for self-describing Arrow IPC streams.</source>
        <translation>解析自我描述的 Arrow IPC 資料串流。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>BLF Loader</source>
        <translation>BLF 載入器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Data loader for Vector BLF (Binary Logging Format) CAN logs, decoded to signals via DBC.</source>
        <translation>載入 Vector BLF（二進位記錄檔格式）CAN 記錄檔，並透過 DBC 解碼為訊號。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>CSV Loader</source>
        <translation>CSV 載入器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Data loader for CSV files.</source>
        <translation>載入 CSV 檔案的資料載入器。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>DataTamer Parser</source>
        <translation>DataTamer 解析器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Message parser for DataTamer encoded data. Efficient serialization for robotics.</source>
        <translation>解析 DataTamer 編碼資料的訊息解析器，為機器人應用提供高效序列化。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Dummy Streamer</source>
        <translation>模擬資料串流</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Generates synthetic sine, cosine, sawtooth, and noise signals for testing and demonstration.</source>
        <translation>產生正弦、餘弦、鋸齒波及雜訊訊號，用於測試與示範。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Foxglove Bridge</source>
        <translation>Foxglove 橋接</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Connect to Foxglove WebSocket server for ROS data streaming. Compatible with Foxglove Studio.</source>
        <translation>連線 Foxglove WebSocket 伺服器以接收 ROS 資料串流，相容 Foxglove Studio。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>JSON Parser</source>
        <translation>JSON 解析器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Message parser for JSON, CBOR, MessagePack, and BSON encoded data.</source>
        <translation>解析 JSON、CBOR、MessagePack 和 BSON 編碼資料的訊息解析器。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>LeRobot Loader</source>
        <translation>LeRobot 載入器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Data loader for LeRobot v2.x and v3.0 datasets: flattened numeric series + per-camera video on a shared timeline. v3.0 datasets use a consolidated per-shard Parquet/MP4 layout with relational metadata; the plugin reads meta/episodes/*.parquet to resolve each episode&apos;s row range and clip window.</source>
        <translation>載入 LeRobot v2.x 和 v3.0 資料集：在共用時間軸上呈現展開的數值序列和各相機影片。v3.0 資料集採用按分片整合的 Parquet/MP4 版面配置和關係中繼資料；外掛程式讀取 meta/episodes/*.parquet，確定每個片段的列範圍和影片裁剪時間段。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Lab Streaming Layer</source>
        <translation>實驗室資料串流層（LSL）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Real-time streaming from Lab Streaming Layer (LSL) sources, including numeric and marker (string) streams.</source>
        <translation>即時接收實驗室資料串流層（LSL）的數值資料串流和標記（字串）資料串流。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>MCAP Loader</source>
        <translation>MCAP 載入器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Data loader for MCAP files and split ROS 2 bags (metadata.yaml). Supports ROS1, ROS2, Protobuf, and JSON message encodings.</source>
        <translation>載入 MCAP 檔案和分卷 ROS 2 資料包（metadata.yaml），支援 ROS1、ROS2、Protobuf 和 JSON 訊息編碼。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>MF4/MDF Loader</source>
        <translation>MF4/MDF 載入器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Data loader for ASAM MDF / MF4 measurement files (automotive, CAN/LIN bus logging).</source>
        <translation>載入 ASAM MDF / MF4 測量檔案（汽車及 CAN/LIN 匯流排記錄檔）。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>MP4 Loader</source>
        <translation>MP4 載入器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Data loader for .mp4 video files. Reads the container&apos;s creation_time tag (when present) so the host can anchor the video on a wall-clock timeline; supports multi-file selection via the standard File dialog.</source>
        <translation>載入 .mp4 影片檔案。讀取容器中的 creation_time 標籤（如存在），供主程式將影片定位到實際時間軸；支援透過標準檔案對話方塊選擇多個檔案。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>MQTT Subscriber</source>
        <translation>MQTT 訂閱器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Real-time data streaming via MQTT protocol. Subscribe to topics and visualize live data.</source>
        <translation>透過 MQTT 通訊協定即時傳輸資料，訂閱主題並視覺化即時資料。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Parquet Loader</source>
        <translation>Parquet 載入器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Data loader for Apache Parquet files. Efficient columnar storage format.</source>
        <translation>載入 Apache Parquet 檔案，這是一種高效的欄式儲存格式。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>PlotJuggler Bridge</source>
        <translation>PlotJuggler 橋接</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Connect to PlotJuggler Bridge server for generic data streaming over WebSocket.</source>
        <translation>連線 PlotJuggler Bridge 伺服器，透過 WebSocket 接收通用資料串流。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>3D Loader (PLY/PCD)</source>
        <translation>3D 載入器（PLY/PCD）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Data loader for static 3D files: .pcd and vertex-only .ply load as a point cloud; .ply with faces loads as a 3D mesh. One snapshot at timestamp 0.</source>
        <translation>載入靜態 3D 檔案：.pcd 和僅含頂點的 .ply 載入為點雲，包含面的 .ply 載入為 3D 網格。在時間戳記 0 處產生一個快照。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Protobuf Parser</source>
        <translation>Protobuf 解析器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Message parser for Protocol Buffers encoded data. Promotes the well-known Foxglove schemas (PointCloud, CompressedVideo, CompressedImage, RawImage, ImageAnnotations, SceneUpdate, FrameTransform, PosesInFrame, CameraCalibration, VoxelGrid, Grid) to builtin scene objects.</source>
        <translation>解析 Protocol Buffers 編碼資料的訊息解析器。將常見 Foxglove 結構定義（PointCloud、CompressedVideo、CompressedImage、RawImage、ImageAnnotations、SceneUpdate、FrameTransform、PosesInFrame、CameraCalibration、VoxelGrid、Grid）轉換為內建場景物件。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>ROS CDR Parser</source>
        <translation>ROS CDR 解析器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Message parser for ROS1 and ROS2 messages (ros1msg, ros2msg, omgidl). Promotes common sensor and visualization messages (Image, PointCloud2, OccupancyGrid, GridMap, TF, Markers, and yolo_msgs/DetectionArray to ImageAnnotations) to builtin scene objects.</source>
        <translation>解析 ROS1 和 ROS2 訊息（ros1msg、ros2msg、omgidl）。將常見感測器和視覺化訊息（Image、PointCloud2、OccupancyGrid、GridMap、TF、Markers，以及轉換為 ImageAnnotations 的 yolo_msgs/DetectionArray）轉換為內建場景物件。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>ROS 2 Topic Subscriber</source>
        <translation>ROS 2 主題訂閱器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Subscribe to ROS 2 topics in real time and stream the decoded fields into PlotJuggler.</source>
        <translation>即時訂閱 ROS 2 主題，將解碼後的欄位傳入 PlotJuggler。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Anomaly Detector</source>
        <translation>異常偵測器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Write Lua anomaly rules over time series and emit plot markers (regions / events) when a rule fires.</source>
        <translation>為時間序列編寫 Lua 異常規則，規則觸發時產生繪圖標記（區域或事件）。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Assistant Agent</source>
        <translation>智慧型助手</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>A chat assistant that drives PlotJuggler through the plugin SDK: lists and describes topics, reads series statistics, and creates derived timeseries, markers and plot tabs it owns. Uses the Claude Code or Codex CLI already installed and signed in on your machine; the plugin stores no API keys. Linux, macOS and Windows.</source>
        <translation>透過外掛程式 SDK 操作 PlotJuggler 的聊天助手：列出和描述主題，讀取序列統計資訊，並建立由其管理的衍生時間序列、標記和繪圖分頁。使用電腦上已安裝並登入的 Claude Code 或 Codex CLI；外掛程式不儲存 API 金鑰。支援 Linux、macOS 和 Windows。</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>CSV/Parquet Exporter</source>
        <translation>CSV/Parquet 匯出器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Export selected time series to CSV or Parquet files.</source>
        <translation>將選取的時間序列匯出為 CSV 或 Parquet 檔案。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Fast Fourier Transform</source>
        <translation>快速傅立葉轉換（FFT）</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Compute the frequency-domain amplitude of numeric time series using FFT.</source>
        <translation>使用 FFT 計算數值時間序列的頻域振幅。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Mosaico Cloud Server</source>
        <translation>Mosaico 雲端伺服器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Browse and import data from Mosaico cloud servers via Apache Arrow Flight. Scalar topics are handed to the host as arrow-ipc messages and decoded by the parser_arrow plugin (install it alongside). Includes Lua metadata predicate filter, multi-topic streaming, and time-range selection.</source>
        <translation>透過 Apache Arrow Flight 瀏覽和匯入 Mosaico 雲端伺服器資料。純量主題以 arrow-ipc 訊息交給主程式，由 parser_arrow 外掛程式解碼（需同時安裝）。支援 Lua 中繼資料條件篩選、多主題資料串流和時間範圍選擇。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Quaternion to RPY</source>
        <translation>四元數轉 RPY</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Converts quaternion (x, y, z, w) time series into Roll, Pitch, Yaw angles with optional unwrapping and degree/radian output.</source>
        <translation>將四元數（x、y、z、w）時間序列轉換為滾轉、俯仰及偏航角，可選擇展開角度，並以角度或弧度輸出。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Transform Editor</source>
        <translation>轉換編輯器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Create named derived time series using Lua functions. Equivalent to the Custom Series editor in PJ3.</source>
        <translation>使用 Lua 函式建立命名的衍生時間序列，相當於 PJ3 的自訂序列編輯器。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>UDP Server</source>
        <translation>UDP 伺服器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Real-time data streaming via UDP. Supports unicast and multicast IPv4/IPv6.</source>
        <translation>透過 UDP 即時傳輸資料，支援 IPv4/IPv6 單播和多播。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>ULog Loader</source>
        <translation>ULog 載入器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Data loader for PX4 ULog files. Flight log format for PX4 autopilot.</source>
        <translation>載入 PX4 自動駕駛儀使用的 ULog 飛行記錄檔。</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>WebRTC Video Client</source>
        <translation>WebRTC 影片用戶端</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Receives live H.264 video via standard WHEP (mediamtx, go2rtc, LiveKit, Cloudflare Stream...) and feeds each stream to PlotJuggler as canonical PJ.VideoFrame messages. One HTTP request per stream, per-camera reconnect, mediamtx Control API discovery. H.264 pass-through; no transcode.</source>
        <translation>透過標準 WHEP（mediamtx、go2rtc、LiveKit、Cloudflare Stream 等）接收即時 H.264 影片，並將各路影片串流以標準 PJ.VideoFrame 訊息傳給 PlotJuggler。每路影片串流使用一個 HTTP 要求，支援逐相機重新連線及 mediamtx Control API 發現。H.264 直接傳輸，不轉碼。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>ZMQ Subscriber</source>
        <translation>ZMQ 訂閱器</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Real-time data streaming via ZeroMQ. High-performance messaging for distributed systems.</source>
        <translation>透過 ZeroMQ 即時傳輸資料，為分散式系統提供高效能訊息傳遞。</translation>
    </message>
</context>
<context>
    <name>PJ::MarketplaceDiagnostics</name>
    <message>
        <location filename="../../pj_marketplace/src/core/DownloadManager.cpp" line="+19"/>
        <source>Archive is larger than the %1-byte limit</source>
        <translation>壓縮檔超過 %1 位元組的限制</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Could not create destination directory: %1</source>
        <translation>無法建立目標目錄：%1</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Could not open ZIP: %1</source>
        <translation>無法開啟 ZIP：%1</translation>
    </message>
    <message>
        <location line="+11"/>
        <location line="+90"/>
        <location line="+196"/>
        <source>Cancelled</source>
        <translation>已取消</translation>
    </message>
    <message>
        <location line="-270"/>
        <source>Unsafe path detected in ZIP entry: %1</source>
        <translation>ZIP 條目包含不安全路徑：%1</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>%1 (at &quot;%2&quot;)</source>
        <translation>%1（位於「%2」）</translation>
    </message>
    <message>
        <location line="+32"/>
        <source>No write permission for: %1</source>
        <translation>沒有寫入權限：%1</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Error reading ZIP entry &apos;%1&apos;: %2</source>
        <translation>讀取 ZIP 條目「%1」時出錯：%2</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>ZIP entry &apos;%1&apos; holds more bytes than it declares</source>
        <translation>ZIP 條目「%1」的實際位元組數超過其宣告值</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>ZIP entry &apos;%1&apos; does not declare its size and expands past the remaining budget</source>
        <translation>ZIP 條目「%1」未宣告大小，且解壓後超過剩餘額度</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Error during extraction: %1</source>
        <translation>解壓時出錯：%1</translation>
    </message>
    <message>
        <location line="+146"/>
        <source>Malformed checksum in registry (&quot;%1&quot; has no digest)</source>
        <translation>註冊表中的檢查碼格式無效（「%1」沒有摘要）</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Checksum mismatch</source>
        <translation>檢查碼不符合</translation>
    </message>
    <message>
        <location filename="../../pj_marketplace/src/core/ExtensionManager.cpp" line="-863"/>
        <source>Extension id is empty</source>
        <translation>擴充功能 ID 為空</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Extension id &quot;%1&quot; is not safe for filesystem paths</source>
        <translation>擴充功能 ID「%1」不能安全地用於檔案系統路徑</translation>
    </message>
    <message>
        <location line="+90"/>
        <source>record names no path</source>
        <translation>記錄未指定路徑</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>record path is not absolute</source>
        <translation>記錄中的路徑不是絕對路徑</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>record targets the extensions store itself</source>
        <translation>記錄指向擴充功能儲存目錄本身</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>record targets a path outside the extensions store</source>
        <translation>記錄指向擴充功能儲存目錄之外</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>record path resolves outside the extensions store</source>
        <translation>記錄中的路徑解析後位於擴充功能儲存目錄之外</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>record path is not a directory</source>
        <translation>記錄中的路徑不是目錄</translation>
    </message>
    <message>
        <location line="+30"/>
        <source>a cleanup record must carry no extension id</source>
        <translation>清理記錄不能包含擴充功能 ID</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>a cleanup record must be filed under a cleanup name</source>
        <translation>清理記錄必須以清理記錄名稱儲存</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>record for &quot;%1&quot; is filed under the name &quot;%2&quot;</source>
        <translation>擴充功能「%1」的記錄以名稱「%2」儲存</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>record could not be opened</source>
        <translation>無法開啟記錄</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>record is not a JSON object</source>
        <translation>記錄不是 JSON 物件</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>record does not declare schema %1</source>
        <translation>記錄未宣告格式版本 %1</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>record declares no known operation</source>
        <translation>記錄未宣告已知操作</translation>
    </message>
    <message>
        <location line="+103"/>
        <source>Ignored a removal record: %1 (&quot;%2&quot;)%3</source>
        <translation>已忽略刪除記錄：%1（「%2」）%3</translation>
    </message>
    <message>
        <location line="+5"/>
        <source> and it could not be quarantined</source>
        <translation>，且無法將其隔離</translation>
    </message>
    <message>
        <location line="+66"/>
        <source>Downloaded artifact must contain exactly one top-level directory named &quot;%1&quot;</source>
        <translation>下載的安裝套件必須且只能包含一個名為「%1」的頂層目錄</translation>
    </message>
    <message>
        <location line="+27"/>
        <location line="+95"/>
        <source>no valid plugin DSO found</source>
        <translation>未找到有效的外掛程式動態函式庫</translation>
    </message>
    <message>
        <location line="-63"/>
        <location line="+93"/>
        <source>multiple embedded plugin ids in one extension directory: &quot;%1&quot; and &quot;%2&quot;</source>
        <translation>同一擴充功能目錄中包含多個外掛程式 ID：「%1」和「%2」</translation>
    </message>
    <message>
        <location line="-85"/>
        <location line="+93"/>
        <source>multiple embedded plugin versions in one extension directory for &quot;%1&quot;</source>
        <translation>同一擴充功能目錄中包含外掛程式「%1」的多個版本</translation>
    </message>
    <message>
        <location line="-45"/>
        <source>plugin admission helper failed</source>
        <translation>外掛程式准入檢查輔助程式失敗</translation>
    </message>
    <message>
        <location line="+75"/>
        <source>Installed artifact is not a valid plugin: %1</source>
        <translation>安裝內容不是有效外掛程式：%1</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Embedded plugin id &quot;%1&quot; does not match registry id &quot;%2&quot;</source>
        <translation>內嵌外掛程式 ID「%1」與註冊表 ID「%2」不一致</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Embedded plugin version &quot;%1&quot; does not match registry version &quot;%2&quot;</source>
        <translation>內嵌外掛程式版本「%1」與註冊表版本「%2」不一致</translation>
    </message>
    <message>
        <location line="+14"/>
        <location line="+11"/>
        <source>Could not write staged install intent: %1</source>
        <translation>無法寫入暫存安裝意圖記錄：%1</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Staged install is missing registry intent</source>
        <translation>暫存安裝缺少註冊表意圖記錄</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Could not read staged install intent: %1</source>
        <translation>無法讀取暫存安裝意圖記錄：%1</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Staged install registry intent is invalid</source>
        <translation>暫存安裝的註冊表意圖記錄無效</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Staged install registry intent has unsafe id: %1</source>
        <translation>暫存安裝的註冊表意圖記錄包含不安全的 ID：%1</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Staged install registry intent has unsafe version &quot;%1&quot;</source>
        <translation>暫存安裝的註冊表意圖記錄包含不安全的版本「%1」</translation>
    </message>
    <message>
        <location line="+102"/>
        <source>Another PlotJuggler instance is managing extensions. Close it and restart PlotJuggler to manage extensions here.</source>
        <translation>另一個 PlotJuggler 執行個體正在管理擴充功能。請關閉該執行個體並重新啟動 PlotJuggler，以在此處管理擴充功能。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Cannot create the extensions lock file. Extensions cannot be installed, updated or removed this session.</source>
        <translation>無法建立擴充功能鎖檔案。本次工作階段無法安裝、更新或移除擴充功能。</translation>
    </message>
    <message>
        <location line="+9"/>
        <location line="+12"/>
        <source>%1 This session can browse installed extensions but cannot install, update or remove them.</source>
        <translation>%1 本次工作階段可以瀏覽已安裝的擴充功能，但無法安裝、更新或移除擴充功能。</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Could not create extensions directory &quot;%1&quot;</source>
        <translation>無法建立擴充功能目錄「%1」</translation>
    </message>
    <message>
        <location line="+197"/>
        <location line="+315"/>
        <source>Install of &quot;%1&quot; is already in progress</source>
        <translation>正在安裝「%1」</translation>
    </message>
    <message>
        <location line="-308"/>
        <source>Cannot read &quot;%1&quot;</source>
        <translation>無法讀取「%1」</translation>
    </message>
    <message>
        <location line="+23"/>
        <location line="+345"/>
        <source>Extraction area &quot;%1&quot; is on a different filesystem than &quot;%2&quot;, so the install could not be completed atomically</source>
        <translation>解壓目錄「%1」與「%2」不在同一檔案系統，無法以原子方式完成安裝</translation>
    </message>
    <message>
        <location line="-317"/>
        <source>ZIP must contain exactly one top-level directory holding the plugin</source>
        <translation>ZIP 必須且只能包含一個存放外掛程式的頂層目錄</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Not a valid plugin package: %1</source>
        <translation>不是有效的外掛程式安裝套件：%1</translation>
    </message>
    <message>
        <location line="+25"/>
        <location line="+244"/>
        <source>Uninstall of &quot;%1&quot; is staged; restart to apply it before installing again</source>
        <translation>已排定解除安裝「%1」；請重新啟動 PlotJuggler 使其生效，再重新安裝</translation>
    </message>
    <message>
        <location line="-179"/>
        <location line="+165"/>
        <source>Extension &quot;%1&quot; is already installed</source>
        <translation>擴充功能「%1」已安裝</translation>
    </message>
    <message>
        <location line="-158"/>
        <source>Replacing &quot;%1&quot; was cancelled: no window is left to confirm it</source>
        <translation>已取消替換「%1」：已無可用於確認的視窗</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Replacing &quot;%1&quot; was cancelled: the window that asked was replaced while the question was open</source>
        <translation>已取消替換「%1」：提出確認問題的視窗在對話方塊開啟期間已被替換</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Replacing &quot;%1&quot; was cancelled</source>
        <translation>已取消替換「%1」</translation>
    </message>
    <message>
        <location line="+25"/>
        <location line="+256"/>
        <source>Could not replace existing staged install directory &quot;%1&quot;</source>
        <translation>無法替換已有的暫存安裝目錄「%1」</translation>
    </message>
    <message>
        <location line="-248"/>
        <location line="+255"/>
        <source>Could not stage install to &quot;%1&quot;</source>
        <translation>無法將安裝暫存至「%1」</translation>
    </message>
    <message>
        <location line="-235"/>
        <location line="+254"/>
        <source>Could not replace existing extension directory &quot;%1&quot;</source>
        <translation>無法替換已有的擴充功能目錄「%1」</translation>
    </message>
    <message>
        <location line="-246"/>
        <source>Could not install to &quot;%1&quot;</source>
        <translation>無法安裝至「%1」</translation>
    </message>
    <message>
        <location line="+13"/>
        <location line="+13"/>
        <source>Post-install validation failed: %1</source>
        <translation>安裝後驗證失敗：%1</translation>
    </message>
    <message>
        <location line="-9"/>
        <source>embedded id changed to &quot;%1&quot;</source>
        <translation>內嵌 ID 已變為「%1」</translation>
    </message>
    <message>
        <location line="+138"/>
        <source>Not enough disk space to install the extension</source>
        <translation>磁碟空間不足，無法安裝擴充功能</translation>
    </message>
    <message>
        <location line="+98"/>
        <source>Could not promote install to &quot;%1&quot;</source>
        <translation>無法將安裝內容正式移入「%1」</translation>
    </message>
    <message>
        <location line="+13"/>
        <location line="+7"/>
        <source>Post-promotion validation failed: %1</source>
        <translation>正式安裝後驗證失敗：%1</translation>
    </message>
    <message>
        <location line="+44"/>
        <source>Installation was cancelled</source>
        <translation>安裝已取消</translation>
    </message>
    <message>
        <location line="+19"/>
        <location line="+95"/>
        <source>Extension &quot;%1&quot; is not installed</source>
        <translation>擴充功能「%1」尚未安裝</translation>
    </message>
    <message>
        <location line="-81"/>
        <source>Extension &quot;%1&quot; ships with the application and cannot be uninstalled</source>
        <translation>擴充功能「%1」隨應用程式附帶，無法解除安裝</translation>
    </message>
    <message>
        <location line="+43"/>
        <source>Could not persist the disabled state for &quot;%1&quot;; uninstall not scheduled</source>
        <translation>無法儲存「%1」的停用狀態；未安排解除安裝</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Could not record the removal of &quot;%1&quot;; uninstall not scheduled</source>
        <translation>無法記錄對「%1」的刪除；未安排解除安裝</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>Extension &quot;%1&quot; does not ship with the application</source>
        <translation>擴充功能「%1」並非應用程式附帶的擴充功能</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Extension &quot;%1&quot; is already at its bundled version</source>
        <translation>擴充功能「%1」已是應用程式附帶版本</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Could not stage the downgrade of &quot;%1&quot;</source>
        <translation>無法暫存「%1」的降級操作</translation>
    </message>
    <message>
        <location line="+39"/>
        <source>Installed version &quot;%1&quot; is newer than registry version &quot;%2&quot;; downgrade is not allowed</source>
        <translation>已安裝版本「%1」比註冊表版本「%2」更新；不允許降級</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Update for &quot;%1&quot; is already staged; restart to apply it</source>
        <translation>「%1」的更新已暫存；請重新啟動 PlotJuggler 使其生效</translation>
    </message>
    <message>
        <location line="+104"/>
        <source> Moved to quarantine: &quot;%1&quot;.</source>
        <translation>已移至隔離目錄：「%1」。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source> Could not remove or quarantine &quot;%1&quot; — manual cleanup required.</source>
        <translation>無法刪除或隔離「%1」，需要手動清理。</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Staged install directory has no id</source>
        <translation>暫存安裝目錄沒有 ID</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Staged install directory &quot;%1&quot; does not match registry id &quot;%2&quot;</source>
        <translation>暫存安裝目錄「%1」與註冊表 ID「%2」不一致</translation>
    </message>
    <message>
        <location line="+27"/>
        <source>Could not back up &quot;%1&quot; before update — staged install left in &quot;%2&quot;</source>
        <translation>更新前無法備份「%1」；暫存安裝保留在「%2」</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Could not promote staged install to &quot;%1&quot;</source>
        <translation>無法將暫存安裝正式移入「%1」</translation>
    </message>
    <message>
        <location line="+10"/>
        <source> Previous version restored.</source>
        <translation>已還原舊版本。</translation>
    </message>
    <message>
        <location line="+89"/>
        <source>record path became a symlink before deletion</source>
        <translation>刪除前記錄中的路徑變成了符號連結</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Refused a removal record at deletion time: %1 (&quot;%2&quot;)</source>
        <translation>刪除時拒絕執行記錄：%1（「%2」）</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Could not remove extension directory &quot;%1&quot;; restart the application or close any process using it</source>
        <translation>無法刪除擴充功能目錄「%1」；請重新啟動應用程式，或關閉正在使用它的處理程序</translation>
    </message>
    <message>
        <location line="+62"/>
        <source>Ignored a legacy uninstall marker: %1</source>
        <translation>已忽略舊版解除安裝標記：%1</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Could not record the cleanup of &quot;%1&quot;; it stays scheduled by its in-payload marker</source>
        <translation>無法記錄對「%1」的清理；其安裝內容中的標記仍保留該清理工作</translation>
    </message>
    <message>
        <location line="+158"/>
        <source> Previous version remains in backup: &quot;%1&quot;.</source>
        <translation>舊版本仍保留在備份中：「%1」。</translation>
    </message>
    <message>
        <location line="+56"/>
        <source>Content-addressed shadow skipped for &quot;%1&quot;: %2</source>
        <translation>已跳過「%1」的內容定址副本：%2</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Could not persist the content-addressed load profile</source>
        <translation>無法儲存內容定址載入設定</translation>
    </message>
    <message>
        <location line="+47"/>
        <source>Content-addressed object for &quot;%1&quot; failed its integrity check; loading the local copy instead. Reinstall to regenerate it.</source>
        <translation>「%1」的內容定址物件未通過完整性檢查；將改為載入本機副本。請重新安裝以重新產生該物件。</translation>
    </message>
    <message>
        <location line="+199"/>
        <source>Could not restore the enabled state of &quot;%1&quot;; it may load differently next launch</source>
        <translation>無法還原「%1」的啟用狀態；下次啟動時其載入行為可能不同</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Could not persist the enabled state of &quot;%1&quot;</source>
        <translation>無法儲存「%1」的啟用狀態</translation>
    </message>
    <message>
        <location filename="../../pj_marketplace/src/core/RegistryManager.cpp" line="+105"/>
        <source>Registry parse error: missing or empty required string field &quot;%1&quot;</source>
        <translation>註冊表解析錯誤：缺少必需的字串欄位「%1」，或該欄位為空</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Registry parse error: field &quot;%1&quot; must be a string</source>
        <translation>註冊表解析錯誤：欄位「%1」必須是字串</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>JSON parse error: %1</source>
        <translation>JSON 解析錯誤：%1</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Registry JSON root must be an object</source>
        <translation>註冊表 JSON 根節點必須是物件</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Registry JSON missing &quot;extensions&quot; array</source>
        <translation>註冊表 JSON 缺少「extensions」陣列</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Each entry in &quot;extensions&quot; must be a JSON object</source>
        <translation>「extensions」中的每個條目都必須是 JSON 物件</translation>
    </message>
    <message>
        <location line="+68"/>
        <source>Registry resolution error: %1</source>
        <translation>註冊表解析錯誤：%1</translation>
    </message>
</context>
<context>
    <name>PJ::MarketplaceWindow</name>
    <message>
        <location filename="../../pj_marketplace/src/ui/marketplace_window.cpp" line="+267"/>
        <source>PlotJuggler Marketplace</source>
        <translation>PlotJuggler 擴充功能市場</translation>
    </message>
    <message>
        <location line="+58"/>
        <source>Name</source>
        <translation>名稱</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Category</source>
        <translation>分類</translation>
    </message>
    <message>
        <location line="+0"/>
        <location line="+644"/>
        <source>Installed</source>
        <translation>已安裝</translation>
    </message>
    <message>
        <location line="-644"/>
        <source>Marketplace</source>
        <translation>擴充功能市場</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Description</source>
        <translation>說明</translation>
    </message>
    <message>
        <location line="+71"/>
        <source>Extension %1 will be enabled after restart</source>
        <translation>擴充功能 %1 將在重新啟動後啟用</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Extension %1 will be disabled after restart</source>
        <translation>擴充功能 %1 將在重新啟動後停用</translation>
    </message>
    <message>
        <location line="+26"/>
        <source>&quot;%1&quot; is already installed at version %2, the same version the archive carries.

Replace it? The replacement is applied the next time PlotJuggler starts.</source>
        <translation>「%1」已安裝版本 %2，與壓縮檔中的版本相同。

是否替換？替換將在下次啟動 PlotJuggler 時生效。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>&quot;%1&quot; is already installed at version %2. The archive carries version %3.

Replace it? The replacement is applied the next time PlotJuggler starts.</source>
        <translation>「%1」已安裝版本 %2，壓縮檔中的版本為 %3。

是否替換？替換將在下次啟動 PlotJuggler 時生效。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Replace installed extension?</source>
        <translation>替換已安裝的擴充功能？</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Replace</source>
        <translation>替換</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Cancel</source>
        <translation>取消</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Loading registry...</source>
        <translation>正在載入註冊表…</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Failed to load registry</source>
        <translation>載入註冊表失敗</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Ready — %1 extensions loaded</source>
        <translation>就緒：已載入 %1 個擴充功能</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Extension %1 staged — will be active after restart</source>
        <translation>擴充功能 %1 已暫存，將在重新啟動後生效</translation>
    </message>
    <message>
        <location line="+24"/>
        <source>%1 is already installed — the archive is identical, nothing changed</source>
        <translation>%1 已安裝；壓縮檔內容完全相同，未作變更</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>%1 v%2 is already installed — the archive is identical, nothing changed</source>
        <translation>%1 v%2 已安裝；壓縮檔內容完全相同，未作變更</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Extension %1 staged — will be uninstalled after restart</source>
        <translation>擴充功能 %1 的解除安裝已暫存，將在重新啟動後完成</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Extension %1 will revert to its bundled version after restart</source>
        <translation>擴充功能 %1 將在重新啟動後還原為內建版本</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Registry error: %1</source>
        <translation>註冊表錯誤：%1</translation>
    </message>
    <message>
        <location line="+33"/>
        <source>Verifying</source>
        <translation>正在驗證</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Extracting</source>
        <translation>正在解壓</translation>
    </message>
    <message>
        <location line="+45"/>
        <source>Installation failed: %1</source>
        <translation>安裝失敗：%1</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Uninstalled %1</source>
        <translation>已解除安裝 %1</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Uninstall failed: %1</source>
        <translation>解除安裝失敗：%1</translation>
    </message>
    <message>
        <location line="+11"/>
        <location line="+618"/>
        <source>Marketplace diagnostic: %1</source>
        <translation>擴充功能市場診斷：%1</translation>
    </message>
    <message>
        <location line="-541"/>
        <source>Update available: v%1</source>
        <translation>有可用更新：v%1</translation>
    </message>
    <message>
        <location line="+149"/>
        <source>⚠ Update to v%1 available, but blocked — %2</source>
        <translation>⚠ 可更新至 v%1，但更新被阻止：%2</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>⚠ Incompatible — %1</source>
        <translation>⚠ 不相容：%1</translation>
    </message>
    <message>
        <location line="+29"/>
        <source>requires PJ %1+</source>
        <translation>需要 PJ %1 或更高版本</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>installed: v%1</source>
        <translation>已安裝：v%1</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Changelog</source>
        <translation>更新記錄</translation>
    </message>
    <message>
        <location filename="../../pj_marketplace/include/pj_marketplace/marketplace_window.hpp" line="+179"/>
        <location filename="../../pj_marketplace/src/ui/marketplace_window.cpp" line="+38"/>
        <source>Installing</source>
        <translation>正在安裝</translation>
    </message>
    <message>
        <location filename="../../pj_marketplace/src/ui/marketplace_window.cpp" line="-876"/>
        <source>Data loaders</source>
        <translation>資料載入器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Data streams</source>
        <translation>資料串流</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Message parsers</source>
        <translation>訊息解析器</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Toolboxes</source>
        <translation>工具箱</translation>
    </message>
    <message>
        <location line="+877"/>
        <source>Needs Restart</source>
        <translation>需要重新啟動</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Update</source>
        <translation>更新</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Local newer</source>
        <translation>本機版本較新</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Install</source>
        <translation>安裝</translation>
    </message>
    <message>
        <location line="+24"/>
        <location line="+16"/>
        <source>Uninstall</source>
        <translation>解除安裝</translation>
    </message>
    <message>
        <location line="-13"/>
        <source>This extension ships with the application and cannot be uninstalled</source>
        <translation>此擴充功能隨應用程式提供，無法解除安裝</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Downgrade to bundled v%1</source>
        <translation>降級到內建版本 v%1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Reverts to the bundled version v%1 on the next launch</source>
        <translation>下次啟動時還原為內建版本 v%1</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>Visit Website</source>
        <translation>前往網站</translation>
    </message>
    <message>
        <location line="+157"/>
        <source>%1 of %2 extensions shown</source>
        <translation>已顯示 %1 個擴充功能，共 %2 個</translation>
    </message>
    <message>
        <location line="+25"/>
        <source>  ·  %1 queued</source>
        <translation>  ·  %1 項排隊中</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>  ·  %1 failed</source>
        <translation>  ·  %1 項失敗</translation>
    </message>
    <message>
        <location line="+58"/>
        <source>Details (%1)</source>
        <translation>詳細資料（%1）</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Details</source>
        <translation>詳細資料</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Install plugin from local ZIP</source>
        <translation>從本機 ZIP 安裝外掛程式</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Plugin package (*.zip)</source>
        <translation>外掛程式套件 (*.zip)</translation>
    </message>
    <message>
        <location line="+50"/>
        <source>Installed %1 from file</source>
        <translation>已從檔案安裝 %1</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Installed %1 v%2 from file</source>
        <translation>已從檔案安裝 %1 v%2</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Installed %1 v%2</source>
        <translation>已安裝 %1 v%2</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Installed %1</source>
        <translation>已安裝 %1</translation>
    </message>
    <message>
        <location line="+83"/>
        <source>Installed version is newer than registry version</source>
        <translation>已安裝的版本高於註冊表中的版本</translation>
    </message>
    <message>
        <location line="+42"/>
        <source>Updating %1 extensions...</source>
        <translation>正在更新 %1 個擴充功能…</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Marketplace Diagnostics</source>
        <translation>擴充功能市場診斷資訊</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>ERROR</source>
        <translation>錯誤</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>INFO</source>
        <translation>資訊</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>No diagnostics.</source>
        <translation>沒有診斷資訊。</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Close</source>
        <translation>關閉</translation>
    </message>
    <message>
        <location line="+51"/>
        <source>An extension change is staged. Restart PlotJuggler to apply it.</source>
        <translation>有一項擴充功能變更等待套用。請重新啟動 PlotJuggler 使其生效。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>%1 extension changes are staged. Restart PlotJuggler to apply them.</source>
        <translation>有 %1 項擴充功能變更等待套用。請重新啟動 PlotJuggler 使其生效。</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Restart required</source>
        <translation>需要重新啟動</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>

Details: %1</source>
        <translation>

詳細資料：%1</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Could not load marketplace registry</source>
        <translation>無法載入擴充功能市場註冊表</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The marketplace registry could not be loaded. Only the extensions already installed on this machine are shown; new extensions and updates are unavailable until it loads correctly.</source>
        <translation>無法載入擴充功能市場註冊表。目前僅顯示本機已安裝的擴充功能；註冊表成功載入之前，無法取得新擴充功能或更新。</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Finished with 1 failure — see Diagnostics for details.</source>
        <translation>已完成，其中 1 項失敗。詳細資料請查看診斷資訊。</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Finished with %1 failures — see Diagnostics for details.</source>
        <translation>已完成，其中 %1 項失敗。詳細資料請查看診斷資訊。</translation>
    </message>
</context>
<context>
    <name>PJ::MessageBox</name>
    <message>
        <location filename="../../pj_plotting/widget/src/PlotWidget.cpp" line="+465"/>
        <location filename="../../pj_widgets/src/MessageBox.cpp" line="+327"/>
        <location line="+8"/>
        <location line="+8"/>
        <source>OK</source>
        <translation>確定</translation>
    </message>
    <message>
        <location filename="../../pj_widgets/src/MessageBox.cpp" line="-190"/>
        <source>Don&apos;t show again.</source>
        <translation>不再顯示。</translation>
    </message>
</context>
<context>
    <name>PJ::PixelInspector</name>
    <message>
        <location filename="../../pj_scene2D/widgets/src/pixel_inspector.cpp" line="+305"/>
        <location line="+86"/>
        <location line="+30"/>
        <source>Position: %1, %2</source>
        <translation>位置：%1，%2</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>Depth:    %1 m</source>
        <translation>深度：%1 m</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Depth:    — (no data)</source>
        <translation>深度：—（無資料）</translation>
    </message>
</context>
<context>
    <name>PJ::PlotDocker</name>
    <message>
        <location filename="../../pj_plotting/widget/src/PlotDocker.cpp" line="+613"/>
        <source>Plugin unavailable</source>
        <translation>外掛程式不可用</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Plugin unavailable: %1</source>
        <translation>外掛程式不可用：%1</translation>
    </message>
</context>
<context>
    <name>PJ::PlotRhiCanvas</name>
    <message>
        <location filename="../../pj_plotting/widget/src/PlotRhiCanvas.cpp" line="+1791"/>
        <source>text atlas %1x%2 exceeds backend texture limit %3</source>
        <translation>文字圖集大小 %1x%2 超出算繪後端的貼圖上限 %3</translation>
    </message>
    <message>
        <location line="+282"/>
        <source>GPU plot renderer unavailable</source>
        <translation>GPU 圖表算繪器不可用</translation>
    </message>
</context>
<context>
    <name>PJ::PlotWidget</name>
    <message>
        <location filename="../../pj_plotting/widget/src/PlotWidget.cpp" line="-91"/>
        <source>%1 vs %2</source>
        <translation>%1 對 %2</translation>
    </message>
    <message>
        <location line="+38"/>
        <location line="+51"/>
        <source>Duplicate name</source>
        <translation>名稱重複</translation>
    </message>
    <message>
        <location line="-51"/>
        <location line="+52"/>
        <source>A curve named &quot;%1&quot; already exists in this plot.</source>
        <translation>此圖表中已存在名為「%1」的曲線。</translation>
    </message>
    <message>
        <location line="+819"/>
        <source>dataset %1</source>
        <translation>資料集 %1</translation>
    </message>
    <message>
        <location line="+335"/>
        <source>Timeseries curves can not be dropped on an XY plot.</source>
        <translation>不能將時間序列曲線拖放到 XY 圖中。</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Create XY plots by dropping two curves on an empty plot.</source>
        <translation>將兩條曲線拖放到空白圖表中，即可建立 XY 圖。</translation>
    </message>
    <message>
        <location line="+57"/>
        <source>&amp;Split Horizontally</source>
        <translation>水平分割(&amp;S)</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>&amp;Split Vertically</source>
        <translation>垂直分割(&amp;S)</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>&amp;Remove ALL curves</source>
        <translation>移除全部曲線(&amp;R)</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>&amp;Zoom Out</source>
        <translation>縮小至全範圍(&amp;Z)</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>&amp;Zoom Out Horizontally</source>
        <translation>水平方向縮小至全範圍(&amp;H)</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>&amp;Zoom Out Vertically</source>
        <translation>垂直方向縮小至全範圍(&amp;V)</translation>
    </message>
    <message>
        <location line="+188"/>
        <source>Apply Filter...</source>
        <translation>套用濾波器…</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Copy</source>
        <translation>複製</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Paste</source>
        <translation>貼上</translation>
    </message>
</context>
<context>
    <name>PJ::PreferencesDialog</name>
    <message>
        <location filename="../src/PreferencesDialog.cpp" line="+103"/>
        <source>Preferences</source>
        <translation>偏好設定</translation>
    </message>
    <message>
        <location line="+37"/>
        <source>Appearance</source>
        <translation>外觀</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Plotting</source>
        <translation>繪圖</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Scene 2D</source>
        <translation>二維場景</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Scene 3D</source>
        <translation>三維場景</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Plugins</source>
        <translation>外掛程式</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Recording</source>
        <translation>錄製</translation>
    </message>
    <message>
        <location line="+85"/>
        <source>global</source>
        <translation>全域</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>per plot</source>
        <translation>每個圖表</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>serious</source>
        <translation>簡潔識別</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>memes</source>
        <translation>趣圖</translation>
    </message>
    <message>
        <location line="+25"/>
        <source>Choose funny images or the serious banner. Both modes support the selected language.</source>
        <translation>選擇趣圖或簡潔橫幅，兩種模式均支援所選介面語言。</translation>
    </message>
    <message>
        <location line="+35"/>
        <source>This folder does not exist.</source>
        <translation>此資料夾不存在。</translation>
    </message>
    <message>
        <location line="+27"/>
        <source>default</source>
        <translation>預設</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>custom</source>
        <translation>自訂</translation>
    </message>
    <message>
        <location line="+30"/>
        <source>Add a plugin folder…</source>
        <translation>新增外掛程式資料夾…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Remove the selected folder</source>
        <translation>移除選取的資料夾</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Add plugin folder</source>
        <translation>新增外掛程式資料夾</translation>
    </message>
    <message>
        <location line="+19"/>
        <location line="+60"/>
        <source>Leave empty to use the default folder: %1</source>
        <translation>留空以使用預設資料夾：%1</translation>
    </message>
    <message>
        <location line="-53"/>
        <source>Choose the recordings folder…</source>
        <translation>選擇錄製資料夾…</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Choose the recordings folder</source>
        <translation>選擇錄製資料夾</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Open the recordings folder</source>
        <translation>開啟錄製資料夾</translation>
    </message>
    <message>
        <location line="+42"/>
        <source>Choose the source cache folder…</source>
        <translation>選擇資料來源快取資料夾…</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Choose the source cache folder</source>
        <translation>選擇資料來源快取資料夾</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Open the source cache folder</source>
        <translation>開啟資料來源快取資料夾</translation>
    </message>
    <message>
        <location line="+9"/>
        <location line="+3"/>
        <source>Fixed by --profile-dir: %1</source>
        <translation>由 --profile-dir 固定為：%1</translation>
    </message>
</context>
<context>
    <name>PJ::RangeCalendarWidget</name>
    <message>
        <location filename="../../pj_widgets/src/DateRangePicker.cpp" line="-339"/>
        <source>January</source>
        <translation>一月</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>February</source>
        <translation>二月</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>March</source>
        <translation>三月</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>April</source>
        <translation>四月</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>May</source>
        <translation>五月</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>June</source>
        <translation>六月</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>July</source>
        <translation>七月</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>August</source>
        <translation>八月</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>September</source>
        <translation>九月</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>October</source>
        <translation>十月</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>November</source>
        <translation>十一月</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>December</source>
        <translation>十二月</translation>
    </message>
</context>
<context>
    <name>PJ::RecentFilesMenu</name>
    <message>
        <location filename="../../pj_widgets/src/RecentFilesMenu.cpp" line="+19"/>
        <source>Clear Recent</source>
        <translation>清除最近記錄</translation>
    </message>
</context>
<context>
    <name>PJ::Scene2DConfigPanel</name>
    <message>
        <location filename="../src/ui/Scene2DConfigPanel.cpp" line="+43"/>
        <source>Layers</source>
        <translation>圖層</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Rotation</source>
        <translation>旋轉</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Rotate every layer clockwise</source>
        <translation>順時針旋轉所有圖層</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Settings</source>
        <translation>設定</translation>
    </message>
</context>
<context>
    <name>PJ::Scene2DDockWidget</name>
    <message>
        <location filename="../../pj_scene2D/widgets/src/Scene2DDockWidget.cpp" line="+279"/>
        <location line="+174"/>
        <source>2D View</source>
        <translation>二維檢視</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>2D View - %1</source>
        <translation>二維檢視 - %1</translation>
    </message>
</context>
<context>
    <name>PJ::Scene2DLayer</name>
    <message>
        <location filename="../../pj_scene2D/widgets/src/layers/scene2d_layer.cpp" line="+46"/>
        <source>No active session</source>
        <translation>沒有作用中的工作階段</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Layer source could not be created</source>
        <translation>無法建立圖層資料來源</translation>
    </message>
</context>
<context>
    <name>PJ::Scene3DConfigPanel</name>
    <message>
        <location filename="../src/ui/Scene3DConfigPanel.cpp" line="+281"/>
        <source>Topics</source>
        <translation>主題</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Settings</source>
        <translation>設定</translation>
    </message>
    <message>
        <location line="+26"/>
        <source>Copy parameters</source>
        <translation>複製參數</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Paste parameters</source>
        <translation>貼上參數</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Apply these parameters to all topics of the same type</source>
        <translation>將這些參數套用到所有同型別的主題</translation>
    </message>
    <message>
        <location line="+118"/>
        <source>Camera</source>
        <translation>相機</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Make the camera follow a TF frame&apos;s position</source>
        <translation>使相機跟隨 TF 座標系的位置</translation>
    </message>
    <message>
        <location line="+1"/>
        <location line="+687"/>
        <source>None</source>
        <translation>無</translation>
    </message>
    <message>
        <location line="-675"/>
        <source>Recenter the camera on the followed frame</source>
        <translation>將相機重新對準所跟隨的座標系</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Follow frame</source>
        <translation>跟隨座標系</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Grid</source>
        <translation>網格</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Line grid</source>
        <translation>線框網格</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Checkerboard</source>
        <translation>棋盤格</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Show/hide the grid</source>
        <translation>顯示或隱藏網格</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Style</source>
        <translation>樣式</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Size (m)</source>
        <translation>大小（公尺）</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Divisions</source>
        <translation>分格數</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Transforms and RobotModel</source>
        <translation>座標轉換與機器人模型</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>Show/hide lines connecting each TF frame to its parent</source>
        <translation>顯示或隱藏各 TF 座標系與其父座標系之間的連線</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Frames size (m)</source>
        <translation>座標系大小（公尺）</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Show/hide the TF frames</source>
        <translation>顯示或隱藏 TF 座標系</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Frames opacity</source>
        <translation>座標系不透明度</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>File</source>
        <translation>檔案</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Topic</source>
        <translation>主題</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>URL</source>
        <translation>URL</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Add a robot model from the selected source</source>
        <translation>從所選來源新增機器人模型</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Model/URDF</source>
        <translation>模型/URDF</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Show/hide visual meshes</source>
        <translation>顯示或隱藏外觀網格</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Meshes opacity</source>
        <translation>網格不透明度</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Show/hide collision meshes</source>
        <translation>顯示或隱藏碰撞網格</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Collision opacity</source>
        <translation>碰撞網格不透明度</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>TF frame whose motion trail to draw</source>
        <translation>要繪製運動軌跡的 TF 座標系</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Add a motion trail for the selected frame</source>
        <translation>新增所選座標系的運動軌跡</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Create Trail</source>
        <translation>建立軌跡</translation>
    </message>
    <message>
        <location line="+183"/>
        <location line="+18"/>
        <source>URDF files (*.urdf *.xml);;All files (*)</source>
        <translation>URDF 檔案 (*.urdf *.xml);;所有檔案 (*)</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Load URDF</source>
        <translation>載入 URDF</translation>
    </message>
    <message>
        <location line="+19"/>
        <location line="+2"/>
        <source>Load robot model</source>
        <translation>載入機器人模型</translation>
    </message>
    <message>
        <location line="-2"/>
        <location line="+2"/>
        <source>No robot description topic in this dataset.</source>
        <translation>此資料集中沒有機器人描述主題。</translation>
    </message>
    <message>
        <location line="+108"/>
        <source>Remove this robot model</source>
        <translation>移除此機器人模型</translation>
    </message>
</context>
<context>
    <name>PJ::Scene3DDockWidget</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/Scene3DDockWidget.cpp" line="+236"/>
        <location line="+378"/>
        <location line="+239"/>
        <location line="+1045"/>
        <location line="+111"/>
        <location line="+3"/>
        <location filename="../../pj_scene3D/widgets/wasm/scene3d_dock_widget_wasm.cpp" line="+162"/>
        <location line="+342"/>
        <location line="+772"/>
        <source>3D View</source>
        <translation>三維檢視</translation>
    </message>
    <message>
        <location line="-1670"/>
        <location filename="../../pj_scene3D/widgets/wasm/scene3d_dock_widget_wasm.cpp" line="-1001"/>
        <source>Orbit</source>
        <translation>環繞</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>XYOrbit</source>
        <translation>XY 平面環繞</translation>
    </message>
    <message>
        <location line="+0"/>
        <location filename="../../pj_scene3D/widgets/wasm/scene3d_dock_widget_wasm.cpp" line="+0"/>
        <source>Fly</source>
        <translation>飛行</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Top-down ortho</source>
        <translation>俯視正交</translation>
    </message>
    <message>
        <location line="+12"/>
        <location filename="../../pj_scene3D/widgets/wasm/scene3d_dock_widget_wasm.cpp" line="+9"/>
        <source>Reset view to default</source>
        <translation>將檢視重設為預設狀態</translation>
    </message>
    <message>
        <location line="+260"/>
        <location line="+239"/>
        <location line="+1159"/>
        <location filename="../../pj_scene3D/widgets/wasm/scene3d_dock_widget_wasm.cpp" line="+220"/>
        <source>3D View - %1</source>
        <translation>三維檢視 - %1</translation>
    </message>
    <message>
        <location line="-1386"/>
        <location filename="../../pj_scene3D/widgets/wasm/scene3d_dock_widget_wasm.cpp" line="-116"/>
        <source>Robot model</source>
        <translation>機器人模型</translation>
    </message>
    <message>
        <location line="+170"/>
        <source>Create trail for &apos;%1&apos;</source>
        <translation>建立「%1」的軌跡</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Set as fixed frame</source>
        <translation>設為固定座標系</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Follow this frame</source>
        <translation>跟隨此座標系</translation>
    </message>
    <message>
        <location line="+577"/>
        <source>Frame &apos;%1&apos; can&apos;t be resolved</source>
        <translation>無法解析座標系「%1」</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Frame &apos;%1&apos; is not connected to fixed frame &apos;%2&apos;</source>
        <translation>座標系「%1」未連接至固定座標系「%2」</translation>
    </message>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/scene3d_dock_widget_wasm.cpp" line="-124"/>
        <source>Fixed frame</source>
        <translation>固定座標系</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>XY Orbit</source>
        <translation>XY 平面環繞</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Top Down</source>
        <translation>俯視</translation>
    </message>
</context>
<context>
    <name>PJ::Search</name>
    <message>
        <location filename="../../pj_widgets/src/Search.cpp" line="+51"/>
        <source>Filter...</source>
        <translation>篩選…</translation>
    </message>
</context>
<context>
    <name>PJ::SourcePromotionHost</name>
    <message>
        <location filename="../src/SourcePromotionHost.cpp" line="+67"/>
        <source>the committed load did not preserve dataset %1</source>
        <translation>已提交的載入未保留資料集 %1</translation>
    </message>
    <message>
        <location line="+44"/>
        <source>promoted</source>
        <translation>已持久化</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>the replacement load was cancelled</source>
        <translation>替換載入已取消</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>the load committed without attaching the source record</source>
        <translation>載入已提交，但未附帶資料來源記錄</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>the replacement load failed</source>
        <translation>替換載入失敗</translation>
    </message>
    <message>
        <location line="+146"/>
        <source>dataset %1 was not produced by this plugin&apos;s ingest</source>
        <translation>資料集 %1 並非由此外掛程式匯入產生</translation>
    </message>
    <message>
        <location line="+22"/>
        <source>the file loader was destroyed</source>
        <translation>檔案載入器已銷毀</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>the file loader rejected the request</source>
        <translation>檔案載入器拒絕了要求</translation>
    </message>
</context>
<context>
    <name>PJ::Splashscreen</name>
    <message>
        <location filename="../src/Splashscreen.cpp" line="+203"/>
        <source>Now you&apos;re plotting</source>
        <translation>現在，開始繪圖吧</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The plot thickens</source>
        <translation>資料的故事，愈發精彩</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Hold my rosbag</source>
        <translation>看好我的 rosbag</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Make your data confess</source>
        <translation>讓資料說出真相</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>More than just curves now</source>
        <translation>如今，不止於曲線</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Better than it has any right to be</source>
        <translation>好用得超乎想像</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Objectively the best. Probably.</source>
        <translation>客觀來說，或許是最好的</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Still better than printf</source>
        <translation>還是比 printf 更直觀</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Friends don&apos;t let friends use printf</source>
        <translation>好朋友，不讓你只用 printf</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Lovingly over-engineered</source>
        <translation>用心打磨，精益求精</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Suspiciously good for a free tool</source>
        <translation>免費工具，也能如此出色</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Opening PlotJuggler. Again.</source>
        <translation>又一次，開啟 PlotJuggler</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Curves were just the beginning</source>
        <translation>曲線，只是開始</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Mostly written by an AI</source>
        <translation>主要由 AI 編寫</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>An AI helped. Allegedly.</source>
        <translation>據說，AI 也幫了忙</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>The bug only happens in production</source>
        <translation>這個問題只在現場出現</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Good thing I recorded the data</source>
        <translation>還好，我錄了資料</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Staring at ten thousand log lines</source>
        <translation>盯著一萬行記錄檔找問題</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>One plot later: found it</source>
        <translation>畫條曲線：找到了</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>It must be the sensor</source>
        <translation>一定是感測器壞了</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>It was milliseconds versus seconds</source>
        <translation>原來是毫秒當成了秒</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Just one more printf</source>
        <translation>再加一行 printf 就能找到</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Drag, drop, mystery solved</source>
        <translation>拖進來一畫，真相大白</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>The demo worked yesterday</source>
        <translation>昨天示範明明還好好的</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Replay the good recording</source>
        <translation>還好有錄好的資料能播放</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>My signal is all noise</source>
        <translation>我的訊號怎麼全是雜訊</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>FFT: allow me to introduce myself</source>
        <translation>FFT：該我出場了</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Two curves, two different clocks</source>
        <translation>兩條曲線，各過各的時間</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Time offset to the rescue</source>
        <translation>時間偏移，一下對齊</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>I forgot to save the layout</source>
        <translation>關了視窗才想起沒存版面配置</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>This time I saved the layout</source>
        <translation>這次我先儲存了版面配置</translation>
    </message>
</context>
<context>
    <name>PJ::StreamingSourceManager</name>
    <message>
        <location filename="../src/StreamingSourceManager.cpp" line="+265"/>
        <source>No stream source selected.</source>
        <translation>未選擇串流資料來源。</translation>
    </message>
    <message>
        <location line="+93"/>
        <source>Stream plugin &apos;%1&apos; not found.</source>
        <translation>未找到串流資料外掛程式「%1」。</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Plugin &apos;%1&apos;: createHandle failed.</source>
        <translation>外掛程式「%1」：createHandle 失敗。</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Could not create the time domain.</source>
        <translation>無法建立時間域。</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>secondary time domain lockstep failed.</source>
        <translation>次級時間域同步失敗。</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>createDataset failed: %1</source>
        <translation>createDataset 失敗：%1</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>secondary createDataset failed: %1</source>
        <translation>次級 createDataset 失敗：%1</translation>
    </message>
    <message>
        <location line="+56"/>
        <source>Plugin &apos;%1&apos;: service registration failed: %2</source>
        <translation>外掛程式「%1」：服務註冊失敗：%2</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Plugin &apos;%1&apos;: bind failed: %2</source>
        <translation>外掛程式「%1」：繫結失敗：%2</translation>
    </message>
    <message>
        <location line="+37"/>
        <source>Plugin contract violation: %1. Reinstall the plugin from the Marketplace.</source>
        <translation>外掛程式介面契約違規：%1。請從擴充功能市場重新安裝此外掛程式。</translation>
    </message>
    <message>
        <location line="+23"/>
        <source>Plugin &apos;%1&apos;: loadConfig (post-dialog) failed: %2</source>
        <translation>外掛程式「%1」：對話方塊關閉後 loadConfig 失敗：%2</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Plugin &apos;%1&apos;: start failed: %2</source>
        <translation>外掛程式「%1」：啟動失敗：%2</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>[stream] %1</source>
        <translation>[串流] %1</translation>
    </message>
</context>
<context>
    <name>PJ::TabbedPlotWidget</name>
    <message>
        <location filename="../../pj_plotting/widget/src/TabbedPlotWidget.cpp" line="+326"/>
        <source>Toggle left panel</source>
        <translation>顯示或隱藏左側面板</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Toggle bottom panel</source>
        <translation>顯示或隱藏底部面板</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Toggle right panel</source>
        <translation>顯示或隱藏右側面板</translation>
    </message>
    <message>
        <location line="+85"/>
        <source>tab%1</source>
        <translation>分頁%1</translation>
    </message>
</context>
<context>
    <name>PJ::TailFollowOverlay</name>
    <message>
        <location filename="../../pj_widgets/src/TailFollowOverlay.cpp" line="+20"/>
        <source>Jump to the latest</source>
        <translation>跳到最新位置</translation>
    </message>
</context>
<context>
    <name>PJ::TimePickerWidget</name>
    <message>
        <location filename="../../pj_widgets/src/DateRangePicker.cpp" line="-96"/>
        <source>From time:</source>
        <translation>開始時間：</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>To time:</source>
        <translation>結束時間：</translation>
    </message>
</context>
<context>
    <name>PJ::Timeline</name>
    <message>
        <location filename="../../pj_widgets/src/Timeline.cpp" line="+605"/>
        <source>Align</source>
        <translation>對齊</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Shift every source so their starts line up at the earliest start</source>
        <translation>平移各資料來源，將它們的起點對齊到最早的起點</translation>
    </message>
    <message>
        <location line="+98"/>
        <source>Streaming: pause playback to interact with the timeline</source>
        <translation>正在接收串流資料：暫停播放後可操作時間軸</translation>
    </message>
</context>
<context>
    <name>PJ::TitleBar</name>
    <message>
        <location filename="../src/TitleBar.cpp" line="+57"/>
        <source>&amp;File</source>
        <translation>檔案(&amp;F)</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&amp;Toolbox</source>
        <translation>工具箱(&amp;T)</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&amp;Help</source>
        <translation>說明(&amp;H)</translation>
    </message>
    <message numerus="yes">
        <location line="+89"/>
        <source>%n extension update(s) available</source>
        <translation>
            <numerusform>%n 個擴充功能有可用更新</numerusform>
        </translation>
    </message>
    <message>
        <location line="+83"/>
        <source>Restore</source>
        <translation>還原</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Maximize</source>
        <translation>最大化</translation>
    </message>
    <message>
        <location line="+60"/>
        <source>New errors</source>
        <translation>新的錯誤</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Diagnostics</source>
        <translation>診斷資訊</translation>
    </message>
</context>
<context>
    <name>PJ::VisualizationPlaceholderWidget</name>
    <message>
        <location filename="../../pj_widgets/src/VisualizationPlaceholderWidget.cpp" line="+81"/>
        <source>&amp;Split Horizontally</source>
        <translation>水平分割(&amp;S)</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>&amp;Split Vertically</source>
        <translation>垂直分割(&amp;S)</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>&amp;Paste</source>
        <translation>貼上(&amp;P)</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Plot</source>
        <translation>繪圖</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>State Transitions</source>
        <translation>狀態變化</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>2D</source>
        <translation>二維</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>3D</source>
        <translation>三維</translation>
    </message>
</context>
<context>
    <name>PJ::XYCurveDialog</name>
    <message>
        <location filename="../../pj_plotting/widget/src/XYCurveDialog.cpp" line="+19"/>
        <source>New XY Curve</source>
        <translation>新增 XY 曲線</translation>
    </message>
</context>
<context>
    <name>PreferencesContent</name>
    <message>
        <location filename="../src/PreferencesDialog.ui" line="+167"/>
        <source>Language:</source>
        <translation>語言：</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Language changes take effect after restarting PlotJuggler.</source>
        <translation>介面語言變更將在重新啟動 PlotJuggler 後生效。</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Theme:</source>
        <translation>主題：</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>Icon size:</source>
        <translation>圖示大小：</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>Icon padding:</source>
        <translation>圖示邊距：</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>Layout padding:</source>
        <translation>版面配置邊距：</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>Layout spacing:</source>
        <translation>版面配置間距：</translation>
    </message>
    <message>
        <location line="+35"/>
        <source>Float precision:</source>
        <translation>浮點數精度：</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>Remove the system window frame and draw PlotJuggler&apos;s own title bar instead. Takes effect the next time PlotJuggler starts.</source>
        <translation>移除系統視窗邊框，改用 PlotJuggler 自繪標題欄。下次啟動 PlotJuggler 時生效。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Frameless window (needs restart):</source>
        <translation>無邊框視窗（需重新啟動）：</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>Render plots on a hardware OpenGL canvas (faster). Applies to newly created plots; existing plots keep their current canvas.</source>
        <translation>使用硬體加速的 OpenGL 畫布繪圖（速度較快）。僅套用於新增圖表，現有圖表會保留目前的畫布。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>OpenGL:</source>
        <translation>OpenGL：</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>What to show on startup: a random meme, or a clean branded banner.</source>
        <translation>啟動時顯示的內容：隨機趣味圖片，或簡潔的品牌橫幅。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Splashscreen:</source>
        <translation>啟動畫面：</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>On startup, quietly check GitHub for a newer PlotJuggler release and show a notification if one is available.</source>
        <translation>啟動時在背景檢查 GitHub 上是否有 PlotJuggler 新版本，並在有更新時顯示通知。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Check for updates on startup:</source>
        <translation>啟動時檢查更新：</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>On startup, send one anonymous ping to count daily users: a hashed machine id, OS name and version, CPU architecture, app version, and package type. Never any personal data, file names, paths, or usage behavior.</source>
        <translation>啟動時傳送一次匿名要求，以統計每日使用者數。內容包括經雜湊處理的機器識別碼、作業系統名稱與版本、CPU 架構、應用程式版本，以及套件類型。不包含任何個人資料、檔案名稱、路徑或使用行為。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Anonymous usage statistics:</source>
        <translation>匿名使用統計：</translation>
    </message>
    <message>
        <location line="+52"/>
        <source>Rescale a plot&apos;s vertical axis to fit its curves whenever a curve is added or removed (the shared time axis is left unchanged).</source>
        <translation>新增或移除曲線時，自動調整圖表縱軸以適合曲線範圍（共用時間軸保持不變）。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Auto-zoom plots:</source>
        <translation>自動縮放圖表：</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>Curves color sequence:</source>
        <translation>曲線配色順序：</translation>
    </message>
    <message>
        <location line="+46"/>
        <source>Coming soon</source>
        <translation>即將推出</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Folders containing 3D assets</source>
        <translation>包含三維資源的資料夾</translation>
    </message>
    <message>
        <location line="+91"/>
        <source>Local folders with custom plugins:</source>
        <translation>自訂外掛程式的本機資料夾：</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>List of default folders (in order of precedence):</source>
        <translation>預設資料夾清單（按優先順序排列）：</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Marketplace registry URL:</source>
        <translation>擴充功能市場註冊表 URL：</translation>
    </message>
    <message>
        <location line="+74"/>
        <source>Every Record press creates one folder here holding one standard MCAP file per recorded source. Recordings capture the raw messages of the topics each stream is subscribed to; sources that write decoded samples directly (no message format) are not recorded.</source>
        <translation>每次點選錄製都會在此建立一個資料夾，為每個參與錄製的資料來源儲存一個標準 MCAP 檔案。錄製內容為各資料串流已訂閱主題的原始訊息；直接寫入解碼後取樣的資料來源（無訊息格式）不會參與錄製。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Recordings folder:</source>
        <translation>錄製資料夾：</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>default: app data folder / recordings</source>
        <translation>預設：應用程式資料資料夾 / recordings</translation>
    </message>
    <message>
        <location line="+18"/>
        <location line="+16"/>
        <source>Memory EACH recorded source may hold in flight. Once a source fills it, that source drops its largest queued messages rather than holding on to them. Recording several sources can hold this much for each of them.</source>
        <translation>每個錄製資料來源允許占用的待寫入記憶體。某個資料來源用滿配額後，會丟棄其佇列中最大的訊息。錄製多個資料來源時，每個資料來源均可分別占用此額度。</translation>
    </message>
    <message>
        <location line="-13"/>
        <source>Write queue per source (MiB):</source>
        <translation>每個資料來源的寫入佇列（MiB）：</translation>
    </message>
    <message>
        <location line="+29"/>
        <source>One MCAP file per recorded source, per Record press. Recording never slows a stream down. Hover a setting for details.</source>
        <translation>每次錄製為每個資料來源儲存一個 MCAP 檔案。錄製不會降低資料串流速度。將滑鼠懸停在設定上可查看詳細資料。</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Local copies of cloud downloads, so a saved layout can restore them instantly and offline. Disposable: a missing entry is simply re-downloaded. A new folder takes effect the next time PlotJuggler starts.</source>
        <translation>儲存雲端下載的本機副本，讓已儲存的版面配置能夠快速離線還原。快取可隨時清理，缺失的條目會重新下載。新的資料夾設定將在下次啟動 PlotJuggler 時生效。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Source cache folder:</source>
        <translation>資料來源快取資料夾：</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>default: app data folder / source_cache</source>
        <translation>預設：應用程式資料資料夾 / source_cache</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Disk space the source cache may occupy. Oldest artifacts are removed first when the budget is exceeded; artifacts a loaded dataset still reads are never removed. A new budget takes effect the next time PlotJuggler starts.</source>
        <translation>資料來源快取可占用的磁碟空間。超出配額時優先移除最舊的檔案；已載入資料集仍在讀取的檔案不會被移除。新的配額將在下次啟動 PlotJuggler 時生效。</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Source cache budget (GB):</source>
        <translation>資料來源快取配額（GB）：</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Disk space the source cache may occupy. Oldest artifacts are removed first when the budget is exceeded; artifacts a loaded dataset still reads are never removed.</source>
        <translation>資料來源快取可占用的磁碟空間。超出配額時優先移除最舊的檔案；已載入資料集仍在讀取的檔案不會被移除。</translation>
    </message>
    <message>
        <location line="+16"/>
        <location line="+16"/>
        <source>When on, each cloud download is also saved into the source cache so a saved layout can restore it offline. Applies immediately; turning it off never removes existing cached copies, and they keep restoring.</source>
        <translation>啟用後，每次雲端下載都會同時寫入資料來源快取，以便已儲存的版面配置離線還原。立即生效；關閉此選項不會移除已有快取，已有快取仍可用於還原。</translation>
    </message>
    <message>
        <location line="-13"/>
        <source>Capture downloads for offline restore:</source>
        <translation>快取下載以供離線還原：</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Cloud downloads are cached locally so saved layouts restore offline. Folder and budget apply at the next start.</source>
        <translation>雲端下載會快取在本機，供已儲存的版面配置離線還原。資料夾和配額變更將在下次啟動時生效。</translation>
    </message>
    <message>
        <location line="+68"/>
        <source>Reset to defaults</source>
        <translation>還原預設設定</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>OK</source>
        <translation>確定</translation>
    </message>
</context>
<context>
    <name>QAbstractFileIconProvider</name>
    <message>
        <location filename="../src/AppLanguage.cpp" line="+83"/>
        <source>Drive</source>
        <translation>磁碟機</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>File</source>
        <translation>檔案</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Unknown</source>
        <translation>未知</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>File Folder</source>
        <comment>Match Windows Explorer</comment>
        <translation>資料夾</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Folder</source>
        <comment>All other platforms</comment>
        <translation>資料夾</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Alias</source>
        <comment>macOS Finder</comment>
        <translation>替身</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Shortcut</source>
        <comment>All other platforms</comment>
        <translation>捷徑</translation>
    </message>
</context>
<context>
    <name>QFileDialog</name>
    <message>
        <location line="-13"/>
        <source>&amp;Look in:</source>
        <translation>尋找範圍(&amp;L)：</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Files of &amp;type:</source>
        <translation>檔案型別(&amp;T)：</translation>
    </message>
</context>
<context>
    <name>QObject</name>
    <message>
        <location filename="../src/DialogPresenter.cpp" line="+76"/>
        <source>File selection failed</source>
        <translation>檔案選擇失敗</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>selected file</source>
        <translation>所選檔案</translation>
    </message>
    <message>
        <location line="+2"/>
        <location filename="../src/FileLoader.cpp" line="-1991"/>
        <location line="+90"/>
        <location line="+7"/>
        <location filename="../src/MainWindow.cpp" line="-9959"/>
        <source>OK</source>
        <translation>確定</translation>
    </message>
    <message>
        <location filename="../src/FileLoader.cpp" line="-92"/>
        <location line="+86"/>
        <location filename="../tests/wasm_acceptance_probes.inc" line="+224"/>
        <location line="+177"/>
        <source>Cancel</source>
        <translation>取消</translation>
    </message>
    <message>
        <location line="-90"/>
        <location line="+91"/>
        <source>Yes</source>
        <translation>是</translation>
    </message>
    <message>
        <location line="-90"/>
        <location line="+91"/>
        <source>No</source>
        <translation>否</translation>
    </message>
    <message>
        <location line="-90"/>
        <location line="+91"/>
        <source>Continue</source>
        <translation>繼續</translation>
    </message>
    <message>
        <location line="-90"/>
        <location line="+91"/>
        <source>Abort</source>
        <translation>中止</translation>
    </message>
    <message>
        <location filename="../tests/wasm_acceptance_probes.inc" line="-322"/>
        <source>File</source>
        <translation>檔案</translation>
    </message>
    <message>
        <location line="+142"/>
        <source>Reselect source</source>
        <translation>重新選擇資料來源</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Select source </source>
        <translation>選擇資料來源 </translation>
    </message>
    <message>
        <location line="+173"/>
        <source>Stop loading?</source>
        <translation>停止載入？</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Remove All</source>
        <translation>全部移除</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Stop and Keep</source>
        <translation>停止並保留</translation>
    </message>
    <message>
        <location line="+377"/>
        <source>Toggle right panel</source>
        <translation>顯示或隱藏右側面板</translation>
    </message>
    <message>
        <location filename="../src/ToolboxPresenter.cpp" line="+263"/>
        <source>Move to a tab</source>
        <translation>移至分頁</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Move to docked panel</source>
        <translation>移至停駐面板</translation>
    </message>
    <message>
        <location filename="../src/ui/CurveListPanel.cpp" line="-822"/>
        <source>Camera calibration topic, used automatically by 2D and 3D views. It cannot be displayed on its own.</source>
        <translation>相機校正主題，由二維和三維檢視自動使用，無法單獨顯示。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Incremental map update, applied automatically to its occupancy grid. It cannot be displayed on its own.</source>
        <translation>地圖增量更新，會自動套用到對應的佔據網格，無法單獨顯示。</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>No view can display this topic type.</source>
        <translation>沒有檢視能夠顯示此主題型別。</translation>
    </message>
    <message>
        <location filename="../src/ui/Scene3DConfigPanel.cpp" line="-824"/>
        <location line="+65"/>
        <source>Robot description topic</source>
        <translation>機器人描述主題</translation>
    </message>
    <message>
        <location line="-51"/>
        <location line="+68"/>
        <source>Load URDF from URL</source>
        <translation>從 URL 載入 URDF</translation>
    </message>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/depth_cloud_layer_wasm.cpp" line="+53"/>
        <source>Depth image payload is invalid</source>
        <translation>深度影像資料無效</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Depth image payload could not be opened</source>
        <translation>無法開啟深度影像資料</translation>
    </message>
    <message>
        <location line="+9"/>
        <location line="+74"/>
        <source>Decoded depth image exceeds the %1-pixel browser limit</source>
        <translation>解碼後的深度影像超出瀏覽器的 %1 像素限制</translation>
    </message>
    <message>
        <location line="-68"/>
        <source>Depth image decode failed: %1</source>
        <translation>深度影像解碼失敗：%1</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Depth image dimensions exceed the %1-pixel browser limit</source>
        <translation>深度影像尺寸超出瀏覽器的 %1 像素限制</translation>
    </message>
    <message>
        <location line="+30"/>
        <source>Not a depth image (encoding &apos;%1&apos;)</source>
        <translation>不是深度影像（編碼為「%1」）</translation>
    </message>
    <message>
        <location line="+374"/>
        <source>Depth image contains no valid pixels in the selected range</source>
        <translation>深度影像在所選範圍內沒有有效像素</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Not enough browser memory to build this DepthCloud</source>
        <translation>瀏覽器記憶體不足，無法建置此深度點雲</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>DepthCloud conversion failed: %1</source>
        <translation>深度點雲轉換失敗：%1</translation>
    </message>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/scene_entities_layer_wasm.cpp" line="+284"/>
        <source>SceneEntities exceeds the browser limit of %1 distinct frames</source>
        <translation>場景實體使用的不同座標系數量超出瀏覽器的 %1 個限制</translation>
    </message>
    <message>
        <location line="+38"/>
        <source>SceneEntities exceeds browser limits (%1 instances, %2 expanded vertices, %3 frames)</source>
        <translation>場景實體超出瀏覽器限制（%1 個執行個體、%2 個展開頂點、%3 個座標系）</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>SceneEntities would retain more than %1 MiB in the browser</source>
        <translation>場景實體將在瀏覽器中占用超過 %1 MiB 記憶體</translation>
    </message>
    <message>
        <location line="+243"/>
        <source>SceneEntities decode received no snapshot</source>
        <translation>場景實體解碼未收到快照</translation>
    </message>
    <message>
        <location line="+193"/>
        <source>Not enough browser memory to build these SceneEntities markers</source>
        <translation>瀏覽器記憶體不足，無法建置這些場景實體標記</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>SceneEntities conversion failed: %1</source>
        <translation>場景實體轉換失敗：%1</translation>
    </message>
    <message>
        <location filename="../../pj_widgets/src/StateTransitionsView.cpp" line="+306"/>
        <source>start</source>
        <translation>開始</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>duration</source>
        <translation>持續時間</translation>
    </message>
    <message>
        <location filename="../src/BrowserPersistence.cpp" line="+581"/>
        <source>The layout is not a bounded, source-free browser recipe.</source>
        <translation>此版面配置不符合瀏覽器版面配置設定的要求：大小受限且不包含資料來源。</translation>
    </message>
    <message>
        <location line="+26"/>
        <source>Browser storage rejected the recent layout recipe; it remains available for this page only.</source>
        <translation>瀏覽器儲存未能儲存此最近使用的版面配置設定；它僅在目前頁面中可用。</translation>
    </message>
    <message>
        <location filename="../../pj_widgets/src/Timeline.cpp" line="-338"/>
        <source>Datasets</source>
        <translation>資料集</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Merge the selected datasets</source>
        <translation>合併選取的資料集</translation>
    </message>
    <message>
        <location filename="../../pj_dialog_host/src/dialog_engine.cpp" line="+500"/>
        <location filename="../../pj_dialog_host/src/panel_engine.cpp" line="+482"/>
        <source>Select File</source>
        <translation>選擇檔案</translation>
    </message>
    <message>
        <location line="+75"/>
        <location filename="../../pj_dialog_host/src/panel_engine.cpp" line="+19"/>
        <source>Select Folder</source>
        <translation>選擇資料夾</translation>
    </message>
    <message>
        <location line="+42"/>
        <location filename="../../pj_dialog_host/src/panel_engine.cpp" line="-10"/>
        <source>Save File</source>
        <translation>儲存檔案</translation>
    </message>
    <message>
        <location filename="../src/BundledAdsTranslationKeys.h" line="+8"/>
        <source>List All Tabs</source>
        <translation>列出所有分頁</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Detach Group</source>
        <translation>分離分組</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Minimize</source>
        <translation>最小化</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Close Tab</source>
        <translation>關閉分頁</translation>
    </message>
</context>
<context>
    <name>QPlatformTheme</name>
    <message>
        <location filename="../src/AppLanguage.cpp" line="-16"/>
        <source>OK</source>
        <translation>確定</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Save</source>
        <translation>儲存</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Save All</source>
        <translation>全部儲存</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Open</source>
        <translation>開啟</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&amp;Yes</source>
        <translation>是(&amp;Y)</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Yes to &amp;All</source>
        <translation>全部選是(&amp;A)</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&amp;No</source>
        <translation>否(&amp;N)</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>N&amp;o to All</source>
        <translation>全部選否(&amp;O)</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Abort</source>
        <translation>中止</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Retry</source>
        <translation>重試</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Ignore</source>
        <translation>忽略</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Close</source>
        <translation>關閉</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Cancel</source>
        <translation>取消</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Discard</source>
        <translation>放棄</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Help</source>
        <translation>說明</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Apply</source>
        <translation>套用</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Reset</source>
        <translation>重設</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Restore Defaults</source>
        <translation>還原預設值</translation>
    </message>
</context>
<context>
    <name>TimelineWidget</name>
    <message>
        <location filename="../src/ui/TimelineWidget.ui" line="+90"/>
        <source>Loop</source>
        <translation>循環播放</translation>
    </message>
    <message>
        <location line="+37"/>
        <source>Start/Stop player (Space)</source>
        <translation>開始或停止播放（空白鍵）</translation>
    </message>
    <message>
        <location line="+76"/>
        <source>Speed</source>
        <translation>速度</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Rate (speed multiplier)</source>
        <translation>速率（播放倍速）</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Step size</source>
        <translation>步進間隔</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Step size to move the time tracker (use the LEFT/RIGHT arrows)</source>
        <translation>移動時間游標的步進間隔（使用左、右方向鍵）</translation>
    </message>
</context>
<context>
    <name>TitleBar</name>
    <message>
        <location filename="../src/TitleBar.ui" line="+136"/>
        <source>UPDATE</source>
        <translation>更新</translation>
    </message>
    <message>
        <location line="+27"/>
        <source>Notifications</source>
        <translation>通知</translation>
    </message>
    <message>
        <location line="+48"/>
        <source>Minimize</source>
        <translation>最小化</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>Maximize</source>
        <translation>最大化</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>Close</source>
        <translation>關閉</translation>
    </message>
</context>
<context>
    <name>ToolboxBanner</name>
    <message>
        <location filename="../src/ToolboxBanner.ui" line="+46"/>
        <source>Move to docked panel</source>
        <translation>移至停駐面板</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Move to a tab</source>
        <translation>移至分頁</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Move to a floating window</source>
        <translation>移至浮動視窗</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Close</source>
        <translation>關閉</translation>
    </message>
</context>
<context>
    <name>XYCurveDialog</name>
    <message>
        <location filename="../../pj_plotting/widget/src/XYCurveDialog.ui" line="+19"/>
        <source>X axis</source>
        <translation>X 軸</translation>
    </message>
    <message>
        <location line="+26"/>
        <source>Swap the X and Y series</source>
        <translation>交換 X 和 Y 序列</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Swap</source>
        <translation>交換</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Y axis</source>
        <translation>Y 軸</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Name</source>
        <translation>名稱</translation>
    </message>
</context>
<context>
    <name>ads::CAutoHideTab</name>
    <message>
        <location filename="../src/BundledAdsTranslationKeys.h" line="+1"/>
        <source>Detach</source>
        <translation>分離</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Pin To...</source>
        <translation>固定到…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Top</source>
        <translation>頂部</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Left</source>
        <translation>左側</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Right</source>
        <translation>右側</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Bottom</source>
        <translation>底部</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Unpin (Dock)</source>
        <translation>取消固定（停駐）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Close</source>
        <translation>關閉</translation>
    </message>
</context>
<context>
    <name>ads::CDockAreaTitleBar</name>
    <message>
        <location line="+1"/>
        <source>Detach</source>
        <translation>分離</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Detach Group</source>
        <translation>分離分組</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Unpin (Dock)</source>
        <translation>取消固定（停駐）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Pin Group</source>
        <translation>固定分組</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Pin Group To...</source>
        <translation>將分組固定到…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Top</source>
        <translation>頂部</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Left</source>
        <translation>左側</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Right</source>
        <translation>右側</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Bottom</source>
        <translation>底部</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Minimize</source>
        <translation>最小化</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Close</source>
        <translation>關閉</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Close Group</source>
        <translation>關閉分組</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Close Other Groups</source>
        <translation>關閉其他分組</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Pin Active Tab (Press Ctrl to Pin Group)</source>
        <translation>固定目前分頁（按 Ctrl 固定分組）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Close Active Tab</source>
        <translation>關閉目前分頁</translation>
    </message>
</context>
<context>
    <name>ads::CDockManager</name>
    <message>
        <location line="+1"/>
        <source>Show View</source>
        <translation>顯示檢視</translation>
    </message>
</context>
<context>
    <name>ads::CDockWidgetTab</name>
    <message>
        <location line="+1"/>
        <source>Detach</source>
        <translation>分離</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Pin</source>
        <translation>固定</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Pin To...</source>
        <translation>固定到…</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Top</source>
        <translation>頂部</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Left</source>
        <translation>左側</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Right</source>
        <translation>右側</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Bottom</source>
        <translation>底部</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Close</source>
        <translation>關閉</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Close Others</source>
        <translation>關閉其他分頁</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::DepthCloudLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/layers/depth_cloud_layer.cpp" line="+290"/>
        <source>Colormap:</source>
        <translation>色彩對映：</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Point size:</source>
        <translation>點大小：</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Min depth:</source>
        <translation>最小深度：</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Max depth:</source>
        <translation>最大深度：</translation>
    </message>
    <message>
        <location line="+241"/>
        <source>Not a depth image (encoding &apos;%1&apos;)</source>
        <translation>不是深度影像（編碼為「%1」）</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>No CameraInfo intrinsics for frame &apos;%1&apos;</source>
        <translation>沒有座標系「%1」對應的 CameraInfo 相機內部參數</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::GridMapLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/layers/grid_map_layer.cpp" line="+264"/>
        <source>Elevation field &apos;%1&apos; not found; using %2</source>
        <translation>未找到高程欄位「%1」；將使用%2</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>a flat plane</source>
        <translation>平面</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Color field &apos;%1&apos; not found</source>
        <translation>未找到顏色欄位「%1」</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Grid map has no scalar field to display</source>
        <translation>網格地圖沒有可顯示的純量欄位</translation>
    </message>
    <message>
        <location line="+47"/>
        <source>Grid map decode failed: %1</source>
        <translation>網格地圖解碼失敗：%1</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Grid map decode returned an object of another type</source>
        <translation>網格地圖解碼傳回了其他型別的物件</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Invalid grid map: %1</source>
        <translation>網格地圖無效：%1</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Grid map too large to display: %1 cells</source>
        <translation>網格地圖過大，無法顯示：%1 個格子</translation>
    </message>
    <message>
        <location line="+224"/>
        <source>None</source>
        <translation>無</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Elevation:</source>
        <translation>高程：</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Color by:</source>
        <translation>著色依據：</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Colors:</source>
        <translation>配色：</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Lighting:</source>
        <translation>光照：</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Opacity:</source>
        <translation>不透明度：</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Auto range:</source>
        <translation>自動範圍：</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Range min:</source>
        <translation>範圍下限：</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Range max:</source>
        <translation>範圍上限：</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::MeshDiagnostics</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/mesh_load_set.h" line="+128"/>
        <source>mesh load threw: %1</source>
        <translation>載入網格時發生例外：%1</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>mesh load threw an unknown exception</source>
        <translation>載入網格時發生未知例外</translation>
    </message>
    <message>
        <location filename="../../pj_scene3D/widgets/src/mesh_loader.cpp" line="+335"/>
        <source>assimp returned no scene for %1</source>
        <translation>Assimp 未傳回 %1 的場景</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>model exceeds browser structure limits in %1 (%2 materials, %3 nodes, depth %4)</source>
        <translation>%1 中的模型超過瀏覽器結構限制（%2 個材質、%3 個節點、深度 %4）</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>model has an invalid or over-limit node graph in %1</source>
        <translation>%1 中的模型節點圖無效或超過限制</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>model has an invalid mesh reference in %1</source>
        <translation>%1 中的模型包含無效的網格參照</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>model vertex count overflow in %1</source>
        <translation>%1 中的模型頂點數量溢位</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>model index count overflow in %1</source>
        <translation>%1 中的模型索引數量溢位</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>model exceeds browser geometry limits in %1 (%2 vertices, %3 indices, %4 submeshes)</source>
        <translation>%1 中的模型超過瀏覽器幾何體限制（%2 個頂點、%3 個索引、%4 個子網格）</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>model exceeds the browser embedded-texture limit in %1</source>
        <translation>%1 中的模型超過瀏覽器內嵌貼圖限制</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>no renderable geometry in %1</source>
        <translation>%1 中沒有可算繪的幾何體</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>model would retain more than %1 MiB in the browser</source>
        <translation>模型將在瀏覽器中占用超過 %1 MiB</translation>
    </message>
    <message>
        <location line="+34"/>
        <location line="+37"/>
        <source>model source exceeds the %1 MiB browser limit</source>
        <translation>模型來源檔案超過瀏覽器的 %1 MiB 限制</translation>
    </message>
    <message>
        <location line="-26"/>
        <source>assimp failed to import %1</source>
        <translation>Assimp 無法匯入 %1</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>mesh import of %1 threw: %2</source>
        <translation>匯入網格 %1 時發生例外：%2</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>mesh import of %1 threw an unknown exception</source>
        <translation>匯入網格 %1 時發生未知例外</translation>
    </message>
    <message>
        <location line="+27"/>
        <source>assimp failed to import %1 buffer</source>
        <translation>Assimp 無法匯入 %1 緩衝區</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>mesh import of %1 buffer threw: %2</source>
        <translation>匯入 %1 緩衝區中的網格時發生例外：%2</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>mesh import of %1 buffer threw an unknown exception</source>
        <translation>匯入 %1 緩衝區中的網格時發生未知例外</translation>
    </message>
    <message>
        <location filename="../../pj_scene3D/widgets/src/passes/grid_map_render_pass.cpp" line="+219"/>
        <source>Grid map %1 x %2 exceeds this GPU&apos;s texture or draw limits</source>
        <translation>網格地圖 %1 × %2 超過此 GPU 的貼圖或繪製限制</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::OccupancyGridLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/layers/occupancy_grid_layer.cpp" line="+471"/>
        <source>Map (grayscale)</source>
        <translation>地圖（灰階）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Costmap</source>
        <translation>代價地圖</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Colors:</source>
        <translation>配色：</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Opacity:</source>
        <translation>不透明度：</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::PointCloudLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/layers/pointcloud_layer.cpp" line="+512"/>
        <source>sphere</source>
        <translation>球體</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>point</source>
        <translation>點</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>cube</source>
        <translation>立方體</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Shape:</source>
        <translation>形狀：</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Point size:</source>
        <translation>點大小：</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Solid</source>
        <translation>純色</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>RGB</source>
        <translation>RGB</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Field: %1</source>
        <translation>欄位：%1</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Color type:</source>
        <translation>著色方式：</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Color config:</source>
        <translation>顏色設定：</translation>
    </message>
    <message>
        <location line="+48"/>
        <source>Invert colormap</source>
        <translation>反轉色彩對映</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Per-point color</source>
        <translation>逐點顏色</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>auto</source>
        <translation>自動</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Range:</source>
        <translation>範圍：</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Range Min:</source>
        <translation>範圍下限：</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Range Max:</source>
        <translation>範圍上限：</translation>
    </message>
    <message>
        <location line="+27"/>
        <source>Show/hide points outside the range</source>
        <translation>顯示或隱藏範圍外的點</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Outside range:</source>
        <translation>範圍外：</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::PosesInFrameLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/layers/poses_in_frame_layer.cpp" line="+442"/>
        <source>Arrow length (m):</source>
        <translation>箭頭長度（公尺）：</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Opacity:</source>
        <translation>不透明度：</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>X Arrow only:</source>
        <translation>僅顯示 X 軸箭頭：</translation>
    </message>
    <message>
        <location line="+18"/>
        <source>Override color:</source>
        <translation>自訂顏色：</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Trace this topic&apos;s pose across the whole time range</source>
        <translation>追蹤此主題在整個時間範圍內的位姿軌跡</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Trail:</source>
        <translation>軌跡：</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::RobotModelLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/layers/robot_model_layer.cpp" line="+194"/>
        <source>Robot model</source>
        <translation>機器人模型</translation>
    </message>
    <message>
        <location line="+458"/>
        <source>Topic</source>
        <translation>主題</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>File</source>
        <translation>檔案</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>URL</source>
        <translation>URL</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Source</source>
        <translation>來源</translation>
    </message>
    <message>
        <location line="+13"/>
        <location line="+147"/>
        <source>No robot description topic in this dataset</source>
        <translation>此資料集中沒有機器人描述主題</translation>
    </message>
    <message>
        <location line="-116"/>
        <source>Browse for a URDF file</source>
        <translation>瀏覽並選擇 URDF 檔案</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Fetch the URDF from this URL</source>
        <translation>從此 URL 取得 URDF</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Locate...</source>
        <translation>尋找…</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Retry</source>
        <translation>重試</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Status</source>
        <translation>狀態</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>e.g. robot1/</source>
        <translation>例如 robot1/</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Frame prefix</source>
        <translation>座標系前綴</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Auto</source>
        <translation>自動</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Visual</source>
        <translation>外觀模型</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Collision</source>
        <translation>碰撞模型</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Display mode</source>
        <translation>顯示模式</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Color</source>
        <translation>顏色</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Ignore COLLADA up_axis</source>
        <translation>忽略 COLLADA 的 up_axis</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Mesh resolution</source>
        <translation>網格資源解析</translation>
    </message>
    <message>
        <location line="+27"/>
        <source>URDF: %1</source>
        <translation>URDF：%1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>%1  •  %2/%3 meshes  •  %4 packages unresolved</source>
        <translation>%1  •  %2/%3 個網格  •  %4 個套件尚未解析</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>%1  •  %2/%2 meshes</source>
        <translation>%1  •  %2/%2 個網格</translation>
    </message>
    <message>
        <location line="+47"/>
        <source>Open URDF</source>
        <translation>開啟 URDF</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>URDF files (*.urdf *.xml);;All files (*)</source>
        <translation>URDF 檔案 (*.urdf *.xml);;所有檔案 (*)</translation>
    </message>
    <message>
        <location line="+26"/>
        <source>Select the folder that contains your robot packages</source>
        <translation>選擇包含機器人套件的資料夾</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Package &apos;%1&apos; not found under &apos;%2&apos; - expected a subdirectory named &apos;%1&apos;</source>
        <translation>在「%2」中找不到套件「%1」；預期應有名為「%1」的子目錄</translation>
    </message>
    <message>
        <location line="+42"/>
        <location line="+177"/>
        <source>No parser for %1</source>
        <translation>沒有適用於 %1 的解析器</translation>
    </message>
    <message>
        <location line="-42"/>
        <source>Fetching %1</source>
        <translation>正在取得 %1</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Fetch failed (%1)</source>
        <translation>取得失敗（%1）</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Failed to read URDF: %1</source>
        <translation>讀取 URDF 失敗：%1</translation>
    </message>
    <message>
        <location line="+27"/>
        <source>Waiting for %1...</source>
        <translation>正在等待 %1…</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Parse error: %1</source>
        <translation>解析錯誤：%1</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Parse error: parser did not return RobotDescription</source>
        <translation>解析錯誤：解析器未傳回 RobotDescription</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Format &apos;%1&apos; is not supported — only URDF</source>
        <translation>不支援「%1」格式；僅支援 URDF</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>URDF: %1  •  %2/%3 meshes  •  %4 packages unresolved</source>
        <translation>URDF：%1  •  %2/%3 個網格  •  %4 個套件尚未解析</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>URDF: %1  •  %2/%2 meshes</source>
        <translation>URDF：%1  •  %2/%2 個網格</translation>
    </message>
    <message numerus="yes">
        <location line="+175"/>
        <source>  •  %n http ref(s) blocked (file-source URDF)</source>
        <translation>
            <numerusform>  •  已阻止 %n 個 HTTP 參照（URDF 來源為檔案）</numerusform>
        </translation>
    </message>
    <message numerus="yes">
        <location line="+3"/>
        <source>  •  %n absolute path(s) missing</source>
        <translation>
            <numerusform>  •  %n 個絕對路徑不存在</numerusform>
        </translation>
    </message>
</context>
<context>
    <name>pj::scene3d::SceneEntitiesLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/layers/scene_entities_layer.cpp" line="+749"/>
        <source>(embedded model)</source>
        <translation>（嵌入式模型）</translation>
    </message>
    <message>
        <location line="+72"/>
        <source>Failed to fetch %1: %2</source>
        <translation>取得 %1 失敗：%2</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Failed to load model %1: %2</source>
        <translation>載入模型 %1 失敗：%2</translation>
    </message>
    <message numerus="yes">
        <location line="+6"/>
        <source>Remote model fetch is disabled — %n model URL(s) blocked. Enable pj_scene3d/allow_remote_model_fetch to allow.</source>
        <translation>
            <numerusform>已停用遠端模型取得，已阻止 %n 個模型 URL。啟用 pj_scene3d/allow_remote_model_fetch 可允許取得。</numerusform>
        </translation>
    </message>
    <message>
        <location line="+100"/>
        <source>Opacity:</source>
        <translation>不透明度：</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>Override color:</source>
        <translation>自訂顏色：</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Wireframe:</source>
        <translation>線框：</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::SceneViewWidget</name>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/scene_view_widget_rhi.cpp" line="+1139"/>
        <source>Occupancy grid is %1 x %2; this browser GPU supports textures up to %3 x %3</source>
        <translation>佔據網格大小為 %1 x %2；此瀏覽器的 GPU 最大支援 %3 x %3 的貼圖</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Could not create the occupancy-grid uniform buffer</source>
        <translation>無法建立佔據網格的 uniform 緩衝區</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Could not allocate the occupancy-grid texture</source>
        <translation>無法分配佔據網格貼圖</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Could not create occupancy-grid shader bindings</source>
        <translation>無法建立佔據網格的著色器繫結</translation>
    </message>
    <message>
        <location line="+34"/>
        <source>Could not create the voxel-grid uniform buffer</source>
        <translation>無法建立體素網格的 uniform 緩衝區</translation>
    </message>
    <message>
        <location line="+24"/>
        <source>Could not allocate the voxel-grid 3D texture</source>
        <translation>無法分配體素網格的三維貼圖</translation>
    </message>
    <message>
        <location line="+23"/>
        <source>Could not create voxel-grid shader bindings</source>
        <translation>無法建立體素網格的著色器繫結</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>The voxel-grid renderer is not available</source>
        <translation>體素網格算繪器不可用</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>This browser GPU does not support 3D textures</source>
        <translation>此瀏覽器的 GPU 不支援三維貼圖</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Voxel grid is %1 x %2 x %3; this browser GPU supports 3D textures up to %4 per dimension</source>
        <translation>體素網格大小為 %1 x %2 x %3；此瀏覽器的 GPU 支援的三維貼圖每個維度最大為 %4</translation>
    </message>
    <message>
        <location line="+137"/>
        <source>A model GPU buffer exceeds the browser addressable limit</source>
        <translation>模型的 GPU 緩衝區超出瀏覽器的可尋址上限</translation>
    </message>
    <message>
        <location line="+27"/>
        <source>A model wireframe buffer exceeds the browser addressable limit</source>
        <translation>模型的線框緩衝區超出瀏覽器的可尋址上限</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Could not allocate model GPU buffers</source>
        <translation>無法分配模型的 GPU 緩衝區</translation>
    </message>
    <message>
        <location line="+41"/>
        <location line="+16"/>
        <source>A model exceeds the browser decoded-texture limit</source>
        <translation>模型超出瀏覽器的解碼後貼圖上限</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Could not decode a model material texture</source>
        <translation>無法解碼模型材質貼圖</translation>
    </message>
    <message>
        <location line="+32"/>
        <source>A model material texture lost its decoded upload state</source>
        <translation>模型材質貼圖的解碼上傳狀態遺失</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Could not allocate a model material texture</source>
        <translation>無法分配模型材質貼圖</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Could not create model material bindings</source>
        <translation>無法建立模型材質繫結</translation>
    </message>
    <message>
        <location line="+844"/>
        <source>Marker instance accounting overflowed the browser limit</source>
        <translation>標記執行個體計數超出瀏覽器上限</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>Markers need %1 submitted instances and %2 streamed vertices; the browser layer limits are %3 and %4</source>
        <translation>標記需要提交 %1 個執行個體並串流傳輸 %2 個頂點；瀏覽器單圖層的上限分別為 %3 和 %4</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Markers need %1 instances and %2 streamed vertices; only %3 and %4 remain in the browser view budget</source>
        <translation>標記需要 %1 個執行個體和 %2 個串流傳輸頂點；瀏覽器檢視的剩餘配額分別僅為 %3 和 %4</translation>
    </message>
    <message>
        <location line="+117"/>
        <source>Models need %1 draws and %2 triangles; the browser layer limits are %3 and %4</source>
        <translation>模型需要 %1 次繪製呼叫和 %2 個三角形；瀏覽器單圖層的上限分別為 %3 和 %4</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Models need %1 draws and %2 triangles; the remaining browser view budget is %3 and %4</source>
        <translation>模型需要 %1 次繪製呼叫和 %2 個三角形；瀏覽器檢視的剩餘配額分別為 %3 和 %4</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Model shadows exceed the browser draw/triangle budget</source>
        <translation>模型陰影超出瀏覽器的繪製呼叫或三角形配額</translation>
    </message>
    <message>
        <location line="+424"/>
        <source>Could not allocate the browser shadow instance buffer</source>
        <translation>無法分配瀏覽器的陰影執行個體緩衝區</translation>
    </message>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/scene_view_widget_rhi_quality.cpp" line="+159"/>
        <source>Shadow rendering disabled by the browser acceptance override</source>
        <translation>瀏覽器驗收測試的覆寫設定已停用陰影算繪</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>A %1 x %1 shadow map exceeds this browser GPU&apos;s %2-pixel texture limit</source>
        <translation>%1 x %1 的陰影貼圖超出此瀏覽器 GPU 的貼圖上限（%2 像素）</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>This browser GPU does not support sampled D32F render targets</source>
        <translation>此瀏覽器的 GPU 不支援可取樣的 D32F 算繪目標</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>The browser shadow shaders are unavailable</source>
        <translation>瀏覽器的陰影著色器不可用</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Could not allocate the browser shadow depth texture</source>
        <translation>無法分配瀏覽器的陰影深度貼圖</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Could not create the browser shadow render target</source>
        <translation>無法建立瀏覽器的陰影算繪目標</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Could not allocate the browser shadow bindings</source>
        <translation>無法分配瀏覽器的陰影繫結</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Could not create the browser shadow resource bindings</source>
        <translation>無法建立瀏覽器的陰影資源繫結</translation>
    </message>
    <message>
        <location line="+32"/>
        <source>Could not create the browser shadow depth pipeline</source>
        <translation>無法建立瀏覽器的陰影深度管線</translation>
    </message>
    <message>
        <location line="+31"/>
        <source>Could not create the browser shadow receiver pipeline</source>
        <translation>無法建立瀏覽器的陰影接收管線</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Could not create the HDR shadow receiver pipeline</source>
        <translation>無法建立 HDR 陰影接收管線</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Could not create the HDR shadow receiver replay pipeline</source>
        <translation>無法建立 HDR 陰影接收重繪管線</translation>
    </message>
    <message>
        <location line="+254"/>
        <source>SSAO rendering disabled by the browser acceptance override</source>
        <translation>瀏覽器驗收測試的覆寫設定已停用 SSAO 算繪</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>The browser HDR depth replay is not ready for SSAO</source>
        <translation>瀏覽器的 HDR 深度重繪尚未就緒，無法用於 SSAO</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Could not allocate the browser SSAO kernel buffer</source>
        <translation>無法分配瀏覽器的 SSAO 核心緩衝區</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Could not preserve the browser replay coverage for SSAO</source>
        <translation>無法為 SSAO 保留瀏覽器的重繪覆蓋資訊</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Could not create the browser SSAO bindings</source>
        <translation>無法建立瀏覽器的 SSAO 繫結</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Could not load the browser SSAO shaders</source>
        <translation>無法載入瀏覽器的 SSAO 著色器</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Could not create the browser SSAO pipeline</source>
        <translation>無法建立瀏覽器的 SSAO 管線</translation>
    </message>
    <message>
        <location line="+37"/>
        <source>EDL rendering disabled by the browser acceptance override</source>
        <translation>瀏覽器驗收測試的覆寫設定已停用 EDL 算繪</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>The browser HDR depth replay is not ready for EDL</source>
        <translation>瀏覽器的 HDR 深度重繪尚未就緒，無法用於 EDL</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Could not preserve the browser depth replay for the EDL mesh mask</source>
        <translation>無法為 EDL 網格遮罩保留瀏覽器的深度重繪</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Could not load the browser EDL mesh-mask shaders</source>
        <translation>無法載入瀏覽器的 EDL 網格遮罩著色器</translation>
    </message>
    <message>
        <location line="+32"/>
        <source>Could not create the browser EDL mesh-mask pipelines</source>
        <translation>無法建立瀏覽器的 EDL 網格遮罩管線</translation>
    </message>
    <message>
        <location line="+112"/>
        <source>HDR rendering disabled by the browser acceptance override</source>
        <translation>瀏覽器驗收測試的覆寫設定已停用 HDR 算繪</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>This browser GPU does not support 4x multisample renderbuffers</source>
        <translation>此瀏覽器的 GPU 不支援 4 倍多重取樣算繪緩衝區</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>This browser GPU does not support the RGBA16F/D32F/RGBA8 HDR attachments</source>
        <translation>此瀏覽器的 GPU 不支援 RGBA16F/D32F/RGBA8 格式的 HDR 附件</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>The %1 x %2 Scene3D view exceeds this browser GPU&apos;s %3-pixel texture limit</source>
        <translation>%1 x %2 的三維場景檢視超出此瀏覽器 GPU 的貼圖上限（%3 像素）</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>The %1 x %2 Scene3D HDR chain needs %3 MiB; the browser per-view limit is %4 MiB</source>
        <translation>%1 x %2 的三維場景 HDR 處理鏈需要 %3 MiB；瀏覽器單檢視的上限為 %4 MiB</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Live Scene3D HDR views would exceed the browser engine&apos;s %1 MiB limit</source>
        <translation>目前三維場景 HDR 檢視將超出瀏覽器引擎的 %1 MiB 上限</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Could not allocate the browser HDR presentation bindings</source>
        <translation>無法分配瀏覽器的 HDR 呈現繫結</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Could not allocate the browser HDR color and depth-replay chain</source>
        <translation>無法分配瀏覽器的 HDR 顏色與深度重繪處理鏈</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Could not create the multisample browser HDR color target and resolve</source>
        <translation>無法建立瀏覽器的多重取樣 HDR 顏色目標及其解析目標</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Could not create the browser single-sample coverage/depth replay target</source>
        <translation>無法建立瀏覽器的單一取樣覆蓋資訊／深度重繪目標</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Could not create the browser HDR presentation bindings</source>
        <translation>無法建立瀏覽器的 HDR 呈現繫結</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Could not load the browser HDR presentation shaders</source>
        <translation>無法載入瀏覽器的 HDR 呈現著色器</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Could not create the browser HDR presentation pipeline</source>
        <translation>無法建立瀏覽器的 HDR 呈現管線</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Could not create the browser HDR geometry pipelines</source>
        <translation>無法建立瀏覽器的 HDR 幾何管線</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::TrailLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/layers/trail_layer.cpp" line="+50"/>
        <location line="+157"/>
        <source>Trail: %1</source>
        <translation>軌跡：%1</translation>
    </message>
    <message>
        <location line="-156"/>
        <location line="+157"/>
        <source>Trail: topic %1</source>
        <translation>軌跡：主題 %1</translation>
    </message>
    <message>
        <location line="+42"/>
        <location line="+37"/>
        <source>waiting for TF</source>
        <translation>正在等待 TF</translation>
    </message>
    <message>
        <location line="+189"/>
        <source>no motion samples for &apos;%1&apos;</source>
        <translation>沒有「%1」的運動樣本</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>&apos;%1&apos; is not connected to fixed frame &apos;%2&apos;</source>
        <translation>「%1」未連接至固定座標系「%2」</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>pose data could not be decoded (%1 message(s) failed)</source>
        <translation>無法解碼位姿資料（%1 條訊息解碼失敗）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>waiting for pose samples</source>
        <translation>正在等待位姿樣本</translation>
    </message>
    <message>
        <location line="+152"/>
        <source>topic %1</source>
        <translation>主題 %1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Tracks:</source>
        <translation>追蹤物件：</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>Thickness (px):</source>
        <translation>線寬（像素）：</translation>
    </message>
    <message>
        <location line="+57"/>
        <source>Past color:</source>
        <translation>過去軌跡顏色：</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Show/hide the path before the current time</source>
        <translation>顯示或隱藏目前時間之前的軌跡</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Future color:</source>
        <translation>未來軌跡顏色：</translation>
    </message>
    <message>
        <location line="+0"/>
        <source>Show/hide the path after the current time</source>
        <translation>顯示或隱藏目前時間之後的軌跡</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::UrdfParser</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/urdf_parser.cpp" line="+109"/>
        <source>URDF mesh reference exceeds the browser string limit</source>
        <translation>URDF 網格參照超過瀏覽器字串長度限制</translation>
    </message>
    <message>
        <location line="+56"/>
        <source>URDF material reference exceeds the browser string limit</source>
        <translation>URDF 材質參照超過瀏覽器字串長度限制</translation>
    </message>
    <message>
        <location line="+72"/>
        <source>Unsupported format: xacro — run `xacro input.xacro &gt; output.urdf` and load the result.</source>
        <translation>不支援 xacro 格式。請執行 `xacro input.xacro &gt; output.urdf`，然後載入產生的檔案。</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>robot_description too large (%1 MiB, limit 32 MiB)</source>
        <translation>robot_description 過大（%1 MiB，上限為 32 MiB）</translation>
    </message>
    <message>
        <location line="+11"/>
        <location line="+11"/>
        <source>Parse error: %1</source>
        <translation>解析錯誤：%1</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Parse error: empty document</source>
        <translation>解析錯誤：文件為空</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Format &apos;%1&apos; is not supported — only URDF</source>
        <translation>不支援格式「%1」，僅支援 URDF</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>URDF exceeds the browser material limit</source>
        <translation>URDF 超過瀏覽器材質數量限制</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>URDF material name exceeds the browser string limit</source>
        <translation>URDF 材質名稱超過瀏覽器字串長度限制</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>URDF exceeds the browser link limit</source>
        <translation>URDF 超過瀏覽器連桿數量限制</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>URDF link name exceeds the browser string limit</source>
        <translation>URDF 連桿名稱超過瀏覽器字串長度限制</translation>
    </message>
    <message>
        <location line="+12"/>
        <location line="+17"/>
        <source>URDF exceeds the browser geometry limit</source>
        <translation>URDF 超過瀏覽器幾何體數量限制</translation>
    </message>
    <message>
        <location line="+27"/>
        <source>URDF exceeds the browser joint limit</source>
        <translation>URDF 超過瀏覽器關節數量限制</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>URDF joint field exceeds the browser string limit</source>
        <translation>URDF 關節欄位超過瀏覽器字串長度限制</translation>
    </message>
    <message>
        <location line="+17"/>
        <source>Parse error: &lt;robot&gt; has no &lt;link&gt; elements</source>
        <translation>解析錯誤：&lt;robot&gt; 中沒有 &lt;link&gt; 元素</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::UrlFetcher</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/url_fetcher.cpp" line="+112"/>
        <source>unsupported URL scheme &apos;%1&apos;</source>
        <translation>不支援的 URL 通訊協定「%1」</translation>
    </message>
    <message>
        <location line="+40"/>
        <source>response exceeds the %1 MiB limit</source>
        <translation>回應超出 %1 MiB 限制</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::VoxelGridLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/src/layers/voxel_grid_layer.cpp" line="+276"/>
        <source>Voxel grid too large to display: %1 voxels (corrupt or unsupported dimensions)</source>
        <translation>體素網格過大，無法顯示：%1 個體素（維度資料已損壞或不支援）</translation>
    </message>
    <message>
        <location line="+207"/>
        <source>Field:</source>
        <translation>欄位：</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Colors:</source>
        <translation>配色：</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>All cells</source>
        <translation>所有格子</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Non-zero</source>
        <translation>非零值</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Threshold</source>
        <translation>閾值</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>In range</source>
        <translation>範圍內</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Draw:</source>
        <translation>繪製：</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Threshold:</source>
        <translation>閾值：</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Auto colormap range</source>
        <translation>自動調整色彩對映範圍</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Range min:</source>
        <translation>範圍下限：</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Range max:</source>
        <translation>範圍上限：</translation>
    </message>
    <message>
        <location line="+35"/>
        <source>Opacity:</source>
        <translation>不透明度：</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::WasmDepthCloudLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/depth_cloud_layer_wasm.cpp" line="-225"/>
        <source>DepthCloud has %1 points; only %2 remain in the browser view budget</source>
        <translation>深度點雲包含 %1 個點；瀏覽器檢視的剩餘配額僅為 %2 個點</translation>
    </message>
    <message>
        <location line="+51"/>
        <source>Depth image could not be decoded: %1</source>
        <translation>無法解碼深度影像：%1</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Not a depth image</source>
        <translation>並非深度影像</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Depth image payload is %1 MiB; the browser limit is %2 MiB</source>
        <translation>深度影像的資料大小為 %1 MiB；瀏覽器上限為 %2 MiB</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Depth image dimensions exceed the %1-pixel browser limit</source>
        <translation>深度影像尺寸超出瀏覽器的 %1 像素限制</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>No CameraInfo intrinsics for frame &apos;%1&apos;</source>
        <translation>沒有座標系「%1」對應的 CameraInfo 相機內部參數</translation>
    </message>
    <message>
        <location line="+328"/>
        <source>Colormap:</source>
        <translation>色彩對映：</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Point size:</source>
        <translation>點大小：</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Min depth:</source>
        <translation>最小深度：</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Max depth:</source>
        <translation>最大深度：</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::WasmOccupancyGridLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/occupancy_grid_layer_wasm.cpp" line="+178"/>
        <source>Layer needs %1 occupancy cells; only %2 remain in the browser view budget</source>
        <translation>圖層需要 %1 個佔據網格格子；瀏覽器檢視的剩餘配額僅為 %2 個</translation>
    </message>
    <message>
        <location line="+71"/>
        <source>Occupancy-grid payload is %1 MiB; the browser limit is %2 MiB</source>
        <translation>佔據網格的資料大小為 %1 MiB；瀏覽器上限為 %2 MiB</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Occupancy grid could not be decoded: %1</source>
        <translation>無法解碼佔據網格：%1</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>This browser layer accepts OccupancyGrid base samples only</source>
        <translation>此瀏覽器圖層僅接受 OccupancyGrid 基礎資料樣本</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Occupancy grid is %1 x %2; the browser limit is %3 cells and %4 per dimension</source>
        <translation>佔據網格大小為 %1 x %2；瀏覽器上限為 %3 個格子，且每個維度不超過 %4</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Occupancy grid has an invalid resolution or origin pose</source>
        <translation>佔據網格的解析度或原點位姿無效</translation>
    </message>
    <message>
        <location line="+30"/>
        <source>Occupancy update lost: source re-read failed</source>
        <translation>佔據網格更新遺失：重新讀取資料來源失敗</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Occupancy update payload exceeds the %1 MiB browser sample limit</source>
        <translation>佔據網格更新的資料大小超出瀏覽器單個樣本的 %1 MiB 上限</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Occupancy update could not be decoded and was skipped: %1</source>
        <translation>無法解碼佔據網格更新，已跳過：%1</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>A paired update sample was not OccupancyGridUpdate and was skipped</source>
        <translation>配對的更新樣本不是 OccupancyGridUpdate，已跳過</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Occupancy update data was shorter than its declared rectangle and was skipped</source>
        <translation>佔據網格更新的資料不足以填充其宣告的矩形區域，已跳過</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Occupancy updates in this seek window exceed the %1 MiB browser limit</source>
        <translation>此定位視窗內的佔據網格更新超出瀏覽器的 %1 MiB 上限</translation>
    </message>
    <message>
        <location line="+149"/>
        <source>Map (grayscale)</source>
        <translation>地圖（灰階）</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Costmap</source>
        <translation>代價地圖</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Colors:</source>
        <translation>配色：</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Opacity:</source>
        <translation>不透明度：</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::WasmPointCloudLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/point_cloud_layer_wasm.cpp" line="+218"/>
        <location line="+12"/>
        <source>Layer has %1 finite points; only %2 remain in the browser view budget</source>
        <translation>圖層包含 %1 個座標為有限值的點；瀏覽器檢視的剩餘配額僅為 %2 個點</translation>
    </message>
    <message>
        <location line="+76"/>
        <source>Point cloud could not be decoded: %1</source>
        <translation>無法解碼點雲：%1</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Compressed cloud payload is %1 MiB; the browser limit is %2 MiB</source>
        <translation>壓縮點雲的資料大小為 %1 MiB；瀏覽器上限為 %2 MiB</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Point-cloud sample has an unexpected canonical type</source>
        <translation>點雲樣本的標準型別與預期不符</translation>
    </message>
    <message>
        <location line="+16"/>
        <location line="+166"/>
        <source>Cloud has %1 points; the browser limit is %2</source>
        <translation>點雲包含 %1 個點；瀏覽器上限為 %2 個點</translation>
    </message>
    <message>
        <location line="-159"/>
        <location line="+161"/>
        <source>Cloud payload is %1 MiB; the browser limit is %2 MiB</source>
        <translation>點雲的資料大小為 %1 MiB；瀏覽器上限為 %2 MiB</translation>
    </message>
    <message>
        <location line="-145"/>
        <source>Not enough browser memory to convert this point cloud</source>
        <translation>瀏覽器記憶體不足，無法轉換此點雲</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Point-cloud conversion failed: %1</source>
        <translation>點雲轉換失敗：%1</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Malformed point cloud was rejected</source>
        <translation>已拒絕格式錯誤的點雲</translation>
    </message>
    <message>
        <location line="+28"/>
        <source>Point cloud contains no finite positions</source>
        <translation>點雲中沒有座標為有限值的點</translation>
    </message>
    <message>
        <location line="+127"/>
        <source>Compressed point cloud could not be decoded: %1</source>
        <translation>無法解碼壓縮點雲：%1</translation>
    </message>
    <message>
        <location line="+248"/>
        <source>sphere</source>
        <translation>球體</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>point</source>
        <translation>點</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>cube</source>
        <translation>立方體</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Shape:</source>
        <translation>形狀：</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Point size:</source>
        <translation>點大小：</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Solid</source>
        <translation>純色</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>RGB</source>
        <translation>RGB</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Field: %1</source>
        <translation>欄位：%1</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Color type:</source>
        <translation>著色方式：</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Solid color:</source>
        <translation>純色：</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Colormap:</source>
        <translation>色彩對映：</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Invert</source>
        <translation>反轉</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>auto</source>
        <translation>自動</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Range:</source>
        <translation>範圍：</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Range Min:</source>
        <translation>範圍下限：</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Range Max:</source>
        <translation>範圍上限：</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Outside opacity:</source>
        <translation>範圍外不透明度：</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Show outside range</source>
        <translation>顯示範圍外的點</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::WasmPosesInFrameLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/poses_in_frame_layer_wasm.cpp" line="+167"/>
        <location line="+12"/>
        <source>Layer needs %1 pose arrows; only %2 remain in the browser view budget</source>
        <translation>圖層需要 %1 個位姿箭頭；瀏覽器檢視的剩餘配額僅為 %2 個</translation>
    </message>
    <message>
        <location line="+47"/>
        <source>Pose payload is %1 MiB; the browser limit is %2 MiB</source>
        <translation>位姿資料大小為 %1 MiB；瀏覽器上限為 %2 MiB</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Pose array could not be decoded: %1</source>
        <translation>無法解碼位姿陣列：%1</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>This browser layer accepts PosesInFrame samples only</source>
        <translation>此瀏覽器圖層僅接受 PosesInFrame 樣本</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Pose array has %1 poses; the browser limit is %2</source>
        <translation>位姿陣列包含 %1 個位姿；瀏覽器上限為 %2 個</translation>
    </message>
    <message>
        <location line="+19"/>
        <source>Not enough browser memory to expand this pose array</source>
        <translation>瀏覽器記憶體不足，無法展開此位姿陣列</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Pose-array expansion failed: %1</source>
        <translation>位姿陣列展開失敗：%1</translation>
    </message>
    <message>
        <location line="+24"/>
        <source>Pose array contains no finite poses</source>
        <translation>位姿陣列中沒有各分量均為有限值的位姿</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Non-finite poses were skipped</source>
        <translation>已跳過包含非有限值的位姿</translation>
    </message>
    <message>
        <location line="+107"/>
        <source>Arrow length (m):</source>
        <translation>箭頭長度（公尺）：</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Opacity:</source>
        <translation>不透明度：</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>X Arrow only:</source>
        <translation>僅顯示 X 軸箭頭：</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Override color:</source>
        <translation>自訂顏色：</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::WasmRobotModelLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/robot_model_layer_wasm.cpp" line="+243"/>
        <source>Robot model</source>
        <translation>機器人模型</translation>
    </message>
    <message>
        <location line="+162"/>
        <source>Select the local URDF again; browser layouts cannot retain host-file access</source>
        <translation>請重新選擇本機 URDF；瀏覽器版面配置無法保留對本機檔案的存取權限</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Only http(s) URDF URLs are supported in the browser</source>
        <translation>瀏覽器僅支援使用 http(s) 的 URDF URL</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Fetching %1</source>
        <translation>正在取得 %1</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Fetch failed (%1)</source>
        <translation>取得失敗（%1）</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Robot description topic is unavailable</source>
        <translation>機器人描述主題不可用</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>No parser for %1</source>
        <translation>沒有適用於 %1 的解析器</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Waiting for %1...</source>
        <translation>正在等待 %1…</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Parse error: %1</source>
        <translation>解析錯誤：%1</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Parse error: parser did not return RobotDescription</source>
        <translation>解析錯誤：解析器未傳回 RobotDescription</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>robot_description exceeds the %1 MiB browser limit</source>
        <translation>robot_description 超出瀏覽器的 %1 MiB 上限</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Format &apos;%1&apos; is not supported — only URDF</source>
        <translation>不支援「%1」格式；僅支援 URDF</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Parsing %1...</source>
        <translation>正在解析 %1…</translation>
    </message>
    <message>
        <location line="+35"/>
        <source>URDF parse threw: %1</source>
        <translation>URDF 解析時發生例外：%1</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>URDF parse threw an unknown exception</source>
        <translation>URDF 解析時發生未知例外</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>Could not parse URDF</source>
        <translation>無法解析 URDF</translation>
    </message>
    <message>
        <location line="+21"/>
        <source>URDF: %1</source>
        <translation>URDF：%1</translation>
    </message>
    <message>
        <location line="+241"/>
        <source>could not start import: %1</source>
        <translation>無法開始匯入：%1</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>could not start import</source>
        <translation>無法開始匯入</translation>
    </message>
    <message>
        <location line="+20"/>
        <source>mesh import threw: %1</source>
        <translation>網格匯入時發生例外：%1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>mesh import threw an unknown exception</source>
        <translation>網格匯入時發生未知例外</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>mesh contains no renderable geometry</source>
        <translation>網格不包含可算繪的幾何體</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>mesh would exceed the browser layer memory limit</source>
        <translation>網格將超出瀏覽器單圖層的記憶體上限</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>could not retain mesh: %1</source>
        <translation>無法保留網格：%1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>could not retain mesh</source>
        <translation>無法保留網格</translation>
    </message>
    <message numerus="yes">
        <location line="+15"/>
        <source> • %n mesh reference(s) unresolved; URL/package paths must be CORS-accessible</source>
        <translation>
            <numerusform> • %n 個網格參照尚未解析；URL／套件路徑必須允許 CORS 跨來源存取</numerusform>
        </translation>
    </message>
    <message numerus="yes">
        <location line="+4"/>
        <source> • %n mesh reference(s) unavailable in the browser sandbox (shown as magenta placeholders)</source>
        <translation>
            <numerusform> • %n 個網格參照在瀏覽器沙箱中不可用（以品紅色預留位置物件顯示）</numerusform>
        </translation>
    </message>
    <message numerus="yes">
        <location line="+9"/>
        <source> • %n mesh load(s) failed (shown as magenta placeholders)</source>
        <translation>
            <numerusform> • %n 個網格載入失敗（以品紅色預留位置物件顯示）</numerusform>
        </translation>
    </message>
    <message>
        <location line="+7"/>
        <source> • %1/%2 meshes</source>
        <translation> • %1/%2 個網格</translation>
    </message>
    <message>
        <location line="+5"/>
        <source> • %1</source>
        <translation> • %1</translation>
    </message>
    <message>
        <location line="+107"/>
        <source>Source</source>
        <translation>來源</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Status</source>
        <translation>狀態</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>e.g. robot1/</source>
        <translation>例如 robot1/</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Frame prefix</source>
        <translation>座標系前綴</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>Auto</source>
        <translation>自動</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Visual</source>
        <translation>外觀模型</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Collision</source>
        <translation>碰撞模型</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Display mode</source>
        <translation>顯示模式</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Color</source>
        <translation>顏色</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Ignore COLLADA up_axis</source>
        <translation>忽略 COLLADA 的 up_axis</translation>
    </message>
    <message>
        <location line="+4"/>
        <source>Retry</source>
        <translation>重試</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>A browser layout cannot reopen a host file automatically. Remove this row and select the URDF again.</source>
        <translation>瀏覽器版面配置無法自動重新開啟本機檔案。請移除此列，再重新選取 URDF。</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::WasmSceneEntitiesLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/scene_entities_layer_wasm.cpp" line="-261"/>
        <source>SceneEntities payload is %1 MiB; the browser limit is %2 MiB</source>
        <translation>SceneEntities 資料大小為 %1 MiB；瀏覽器上限為 %2 MiB</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>SceneEntities could not be decoded: %1</source>
        <translation>無法解碼 SceneEntities：%1</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Object parser returned the wrong type for SceneEntities</source>
        <translation>物件解析器為 SceneEntities 傳回了錯誤的型別</translation>
    </message>
    <message>
        <location line="+381"/>
        <source>SceneEntities model state would retain more than %1 MiB in the browser</source>
        <translation>SceneEntities 模型狀態將在瀏覽器中占用超過 %1 MiB 的空間</translation>
    </message>
    <message>
        <location line="+14"/>
        <source>A SceneEntities model snapshot was lost: source re-read failed</source>
        <translation>SceneEntities 模型快照遺失：重新讀取資料來源失敗</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>A SceneEntities model snapshot exceeds the %1 MiB browser payload limit</source>
        <translation>SceneEntities 模型快照超出瀏覽器的 %1 MiB 資料大小上限</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>SceneEntities model history could not be decoded: %1</source>
        <translation>無法解碼 SceneEntities 模型歷史記錄：%1</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Object parser returned the wrong type for SceneEntities model history</source>
        <translation>物件解析器為 SceneEntities 模型歷史記錄傳回了錯誤的型別</translation>
    </message>
    <message>
        <location line="+118"/>
        <source>SceneEntities has more than %1 live browser model draws</source>
        <translation>SceneEntities 在瀏覽器中目前所需的模型繪製呼叫超過 %1 次</translation>
    </message>
    <message numerus="yes">
        <location line="+2"/>
        <source>Skipped %n model(s) with an invalid pose or scale</source>
        <translation>
            <numerusform>已跳過 %n 個位姿或縮放無效的模型</numerusform>
        </translation>
    </message>
    <message>
        <location line="+31"/>
        <source>(embedded model)</source>
        <translation>（嵌入式模型）</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>model has neither embedded data nor a URL</source>
        <translation>模型既沒有嵌入資料，也沒有 URL</translation>
    </message>
    <message>
        <location line="+22"/>
        <source>model source exceeds the %1 MiB browser limit</source>
        <translation>模型來源資料超出瀏覽器的 %1 MiB 上限</translation>
    </message>
    <message>
        <location line="+13"/>
        <source>could not queue model import: %1</source>
        <translation>無法將模型匯入工作加入佇列：%1</translation>
    </message>
    <message>
        <location line="+3"/>
        <source>could not queue model import</source>
        <translation>無法將模型匯入工作加入佇列</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>remote model fetch is disabled</source>
        <translation>已停用遠端模型取得</translation>
    </message>
    <message>
        <location line="+63"/>
        <source>could not start model import: %1</source>
        <translation>無法開始匯入模型：%1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>could not start model import</source>
        <translation>無法開始匯入模型</translation>
    </message>
    <message>
        <location line="+25"/>
        <source>mesh load threw: %1</source>
        <translation>網格載入時發生例外：%1</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>mesh load threw an unknown exception</source>
        <translation>網格載入時發生未知例外</translation>
    </message>
    <message>
        <location line="+25"/>
        <source>model would exceed the %1 MiB browser layer memory limit</source>
        <translation>模型將超出瀏覽器單圖層的 %1 MiB 記憶體上限</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>could not retain model: %1</source>
        <translation>無法保留模型：%1</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>could not retain model</source>
        <translation>無法保留模型</translation>
    </message>
    <message>
        <location line="+26"/>
        <source>Failed to load %1: %2</source>
        <translation>載入 %1 失敗：%2</translation>
    </message>
    <message numerus="yes">
        <location line="+4"/>
        <source>Remote model fetch is disabled — %n URL(s) blocked</source>
        <translation>
            <numerusform>已停用遠端模型取得，已阻止 %n 個 URL</numerusform>
        </translation>
    </message>
    <message>
        <location line="+168"/>
        <source>Opacity:</source>
        <translation>不透明度：</translation>
    </message>
    <message>
        <location line="+15"/>
        <source>Override color:</source>
        <translation>自訂顏色：</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Wireframe:</source>
        <translation>線框：</translation>
    </message>
</context>
<context>
    <name>pj::scene3d::WasmVoxelGridLayer</name>
    <message>
        <location filename="../../pj_scene3D/widgets/wasm/voxel_grid_layer_wasm.cpp" line="+194"/>
        <location line="+14"/>
        <source>Layer needs %1 voxels; only %2 remain in the browser view budget</source>
        <translation>圖層需要 %1 個體素；瀏覽器檢視的剩餘配額僅為 %2 個</translation>
    </message>
    <message>
        <location line="+53"/>
        <source>Voxel-grid payload is %1 MiB; the browser limit is %2 MiB</source>
        <translation>體素網格的資料大小為 %1 MiB；瀏覽器上限為 %2 MiB</translation>
    </message>
    <message>
        <location line="+12"/>
        <source>Voxel grid could not be decoded: %1</source>
        <translation>無法解碼體素網格：%1</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>This browser layer accepts VoxelGrid samples only</source>
        <translation>此瀏覽器圖層僅接受 VoxelGrid 樣本</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Voxel grid is %1 x %2 x %3 (%4 voxels); the browser layer limit is %5</source>
        <translation>體素網格大小為 %1 x %2 x %3（%4 個體素）；瀏覽器單圖層的上限為 %5 個體素</translation>
    </message>
    <message>
        <location line="+11"/>
        <source>Voxel grid has an invalid cell size or origin pose</source>
        <translation>體素網格的格子尺寸或原點位姿無效</translation>
    </message>
    <message>
        <location line="+8"/>
        <source>Voxel grid has no displayable fields</source>
        <translation>體素網格沒有可顯示的欄位</translation>
    </message>
    <message>
        <location line="+16"/>
        <source>Not enough browser memory to pack this voxel grid</source>
        <translation>瀏覽器記憶體不足，無法封裝此體素網格</translation>
    </message>
    <message>
        <location line="+6"/>
        <source>Voxel-grid packing failed: %1</source>
        <translation>體素網格封裝失敗：%1</translation>
    </message>
    <message>
        <location line="+9"/>
        <source>Voxel grid field layout could not be packed</source>
        <translation>無法封裝體素網格的欄位排列</translation>
    </message>
    <message>
        <location line="+212"/>
        <source>Field:</source>
        <translation>欄位：</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Turbo</source>
        <translation>Turbo</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Viridis</source>
        <translation>Viridis</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Plasma</source>
        <translation>Plasma</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Grayscale</source>
        <translation>灰階</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Colors:</source>
        <translation>配色：</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>All cells</source>
        <translation>所有格子</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Non-zero</source>
        <translation>非零值</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>Threshold</source>
        <translation>閾值</translation>
    </message>
    <message>
        <location line="+1"/>
        <source>In range</source>
        <translation>範圍內</translation>
    </message>
    <message>
        <location line="+2"/>
        <source>Draw:</source>
        <translation>繪製：</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Threshold:</source>
        <translation>閾值：</translation>
    </message>
    <message>
        <location line="+5"/>
        <source>Auto colormap range</source>
        <translation>自動調整色彩對映範圍</translation>
    </message>
    <message>
        <location line="+10"/>
        <source>Range min:</source>
        <translation>範圍下限：</translation>
    </message>
    <message>
        <location line="+7"/>
        <source>Range max:</source>
        <translation>範圍上限：</translation>
    </message>
    <message>
        <location line="+28"/>
        <source>Opacity:</source>
        <translation>不透明度：</translation>
    </message>
</context>
</TS>
