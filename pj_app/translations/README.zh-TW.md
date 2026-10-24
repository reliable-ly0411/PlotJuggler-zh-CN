# 繁體中文（台灣）翻譯目錄

`plotjuggler4_zh_TW.ts` 是獨立維護的 Qt TS 目錄，語系代碼為 `zh_TW`，
英文來源語系為 `en_US`。介面使用台灣常見的軟體與資料處理用語；程式不會在執行時
把簡體中文自動轉成繁體中文。

## 來源與審閱範圍

初稿以現有 `plotjuggler4_zh_CN.ts` 為基礎，來源提交為
`9f38ffd4bd625723ef96c8a49ad320846b98bc2b`，並同步本次新增 `zh_TW` 選項的
命令列說明來源字串。字形初稿使用系統既有的
[ICU 簡繁轉換](https://unicode-org.github.io/icu/userguide/transforms/general/)，
再修訂台灣用語及重要上下文；這不是僅做字形替換的目錄。
ICU 不是應用程式或翻譯建置流程新增的相依套件。

修訂特別區分了檔案／文件、欄／列、套用／應用程式、覆寫／覆蓋資訊、
座標系／影片影格，以及統計濾波器的變異數、微分、取樣點與時間視窗。
通訊協定、URL、命令、外掛程式 ID、格式字串、數值及 Qt 占位符保留其用途。
英文來源、Qt 上下文、複數旗標與訊息定位資訊不因翻譯而變更。

目前共有 **1,968 條有效訊息**，含 **26 條複數訊息**，沒有空白或
`unfinished` 條目；其中 **29 條**是原樣保留的名稱、識別資訊或格式字串。
這些數字只表示目前 Qt 可擷取訊息的目錄覆蓋率，不表示全部可見文字都已翻譯，
也不表示已逐條通過繁中母語使用者的人工審校。

## 用語約定

- File／Folder：檔案／資料夾；Save／Load：儲存／載入。
- Preferences／Settings：偏好設定／設定；Apply：套用。
- Data／Dataset／Data source：資料／資料集／資料來源。
- Row／Column／Field：列／欄／欄位；文字檔的 line number 仍使用「行」。
- Stream／Topic／Metadata：串流／主題／中繼資料。
- Plugin／Extension：外掛程式／擴充功能；檔案的 extension 則是「副檔名」。
- Layout／Tab／Window：版面配置／分頁／視窗。
- Server／Client／Connection：伺服器／用戶端／連線。
- Memory／Cache／Byte：記憶體／快取／位元組。
- Timestamp／Sample：時間戳記／取樣；方差採用「變異數」。

## 維護與驗證

在儲存庫根目錄使用與應用程式相同的 Qt 工具鏈：

```sh
python3 tests/check_translations_4x.py --language zh_TW --lupdate /path/to/lupdate
```

檢查涵蓋來源集合與上下文、占位符及其數量、複數形式、富文字標籤與屬性。
`--catalog-only` 不會驗證來源覆蓋率，不能取代上述完整檢查。
需要更新來源集合時加上 `--update-ts`，之後應逐一翻譯新增項目，
不要用執行時轉換或英文回退掩蓋未完成訊息。
用語調整須核對完整片語；例如「繪圖標記」與「繪圖分頁」不可被 icon 的「圖示」
替換規則誤改。通過結構檢查不代表譯文語意已正確。

本次目錄已通過來源擷取比對、XML／占位符／複數／富文字檢查，並可由 Qt
`lrelease` 編譯成 1,968 條完成訊息。簡中與繁中目錄的來源、註解、順序、
定位資訊及複數旗標一致；URL 亦已檢查。目錄維護不更動資料解析或數值格式的 locale。

仍須另外驗證：繁中母語使用者審校、實際 Linux／Windows 桌面上的字型與文字截斷、
完整封裝產品，以及不經這些 Qt 翻譯鍵顯示的第三方外掛程式文字。
點陣圖片內的文字、安裝程式與外部網站也不會因新增此 TS 檔而自動翻譯。
