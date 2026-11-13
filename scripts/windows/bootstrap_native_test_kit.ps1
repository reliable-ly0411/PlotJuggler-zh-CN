# SPDX-License-Identifier: MPL-2.0
<#
  This script is a trust root, not part of the kit it verifies. The caller must
  independently authenticate THESE script bytes and the archive and manifest
  hashes, source/tree and configuration before invoking Microsoft PowerShell.
  It intentionally never runs a kit executable, Python, DLL, import or review.
  Before launch, the caller must independently inspect and create the exact empty
  TrustedTemp directory under the test root, including its ancestry and streams.
  Its inherited process TEMP/TMP and CodeDom temporary files are bound there; this
  configuration does not prove all Windows components write nowhere else.
  Run only on a clean, exclusively controlled Windows host. Failure never cleans
  partial output. A receipt describes the instant verified, not runtime safety,
  dynamic dependency closure, or protection against later concurrent mutation.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][string]$ArchiveSha256,
    [Parameter(Mandatory=$true)][string]$ManifestSha256,
    [Parameter(Mandatory=$true)][string]$SourceSha,
    [Parameter(Mandatory=$true)][string]$SourceTree,
    [Parameter(Mandatory=$true)][string]$Configuration,
    [Parameter(Mandatory=$true)][string]$TrustedTemp
)
$ErrorActionPreference = 'Stop'
try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Windows is required' }
    if ($SourceSha -cnotmatch '^[0-9a-f]{40}$') { throw 'SourceSha must be a full lowercase hash' }
    $expectedTemp = 'C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a\bootstrap-temp\' + $SourceSha.Substring(0, 12)
    if ($TrustedTemp -cne $expectedTemp) { throw 'TrustedTemp differs from the independently inspected test directory' }
    for ($path = $TrustedTemp; $null -ne $path; $path = [IO.Path]::GetDirectoryName($path)) {
        $item = [IO.DirectoryInfo]::new($path)
        if (-not $item.Exists -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'TrustedTemp ancestry is missing or a reparse point' }
    }
    if ([IO.Directory]::GetFileSystemEntries($TrustedTemp).Length -ne 0) { throw 'TrustedTemp must be empty' }
    # The trusted caller must set both before PowerShell starts; this process
    # never changes machine-wide or user-wide environment settings.
    if ($env:TEMP -cne $TrustedTemp -or $env:TMP -cne $TrustedTemp) { throw 'TEMP and TMP were not set before PowerShell launch' }
    if ([IO.Path]::GetTempPath().TrimEnd([char]'\') -cne $TrustedTemp) { throw 'Process temporary path differs' }
    $expectedHost = [IO.Path]::Combine([Environment]::SystemDirectory, 'WindowsPowerShell', 'v1.0', 'powershell.exe')
    $actualHost = [Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    if (-not [Environment]::Is64BitProcess -or $PSVersionTable.PSEdition -ne 'Desktop' -or
        $PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1 -or
        -not [string]::Equals($actualHost, $expectedHost, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Use 64-bit Microsoft system Windows PowerShell 5.1'
    }
    # Fully qualified framework identities and GAC locations avoid resolving a
    # same-named DLL from the downloaded kit or the current working directory.
    $assemblies = @(
        [Reflection.Assembly]::Load('System, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089')
        [Reflection.Assembly]::Load('System.Core, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089')
        [Reflection.Assembly]::Load('System.IO.Compression, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089')
        [Reflection.Assembly]::Load('System.IO.Compression.FileSystem, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089')
    )
    foreach ($assembly in $assemblies) {
        if (-not $assembly.GlobalAssemblyCache -or -not $assembly.Location) { throw 'A required Microsoft framework assembly is not in the GAC' }
    }
    # The entire verifier is compiled from this independently trusted script,
    # not from the archive or another file located inside the kit.
    $code = @'
using System;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
using System.Text.RegularExpressions;

public static class NativeKitBootstrap {
    const long MaxArchive = 16L * 1024 * 1024 * 1024;
    const long MaxFile = 8L * 1024 * 1024 * 1024;
    const long MaxTotal = 32L * 1024 * 1024 * 1024;
    const long Reserve = 2L * 1024 * 1024 * 1024;
    const int MaxManifest = 32 * 1024 * 1024;
    const int MaxEntries = 100000;
    const string Manifest = "_bundle/manifest.json";
    const string Origins = "_bundle/origins.json";
    const string Base = @"C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a\n\";
    static readonly StringComparer CI = StringComparer.OrdinalIgnoreCase;
    static readonly Regex H40 = new Regex(@"\A[0-9a-f]{40}\z");
    static readonly Regex H64 = new Regex(@"\A[0-9a-f]{64}\z");
    static readonly Regex Device = new Regex(@"\A(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9\u00b9\u00b2\u00b3]|LPT[1-9\u00b9\u00b2\u00b3])\z", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
    static readonly string[] Required = { "t/python/python.exe", "t/python/python3.dll", "t/python/python312.dll", "t/python/python312.zip", "t/python/python312._pth", "s/scripts/windows/run_native_test_bundle.py", "s/scripts/windows/native_bundle_audit.py", "s/scripts/windows/native_test_review.py", Origins };
    static void Check(bool value, string message) { if (!value) throw new InvalidDataException(message); }
    static string Hash(byte[] bytes) { using (SHA256 h = SHA256.Create()) return Hex(h.ComputeHash(bytes)); }
    static string Hash(Stream stream) { using (SHA256 h = SHA256.Create()) return Hex(h.ComputeHash(stream)); }
    static string Hex(byte[] bytes) { StringBuilder s = new StringBuilder(bytes.Length * 2); foreach (byte b in bytes) s.Append(b.ToString("x2")); return s.ToString(); }
    static Dictionary<string, object> Obj(object x) { var d = x as Dictionary<string, object>; Check(d != null, "expected JSON object"); return d; }
    static List<object> Arr(object x) { var a = x as List<object>; Check(a != null, "expected JSON array"); return a; }
    static object Field(Dictionary<string, object> d, string key) { object v; Check(d.TryGetValue(key, out v), "required JSON field is missing"); return v; }
    static string Str(object x) { string s = x as string; Check(s != null, "expected JSON string"); return s; }
    static long Int(object x) { Check(x is long, "expected integral JSON number"); return (long)x; }
    static string Line(object x) { string s = Str(x); Check(s.Length > 0 && s.Length <= 256 && s.Trim().Length > 0 && s.IndexOfAny(new char[]{'\r','\n','\0'}) < 0, "invalid provenance field"); return s; }

    // Strict JSON, including duplicate/case-colliding member rejection. The
    // manifest contains only integer numbers; fractions/exponents fail closed.
    sealed class Json {
        readonly string s; int i; int depth;
        Json(string s) { this.s = s; }
        public static object Parse(byte[] b) { var p = new Json(new UTF8Encoding(false, true).GetString(b)); object o = p.Value(); p.Ws(); Check(p.i == p.s.Length, "trailing JSON data"); return o; }
        void Ws() { while (i < s.Length && (s[i] == ' ' || s[i] == '\t' || s[i] == '\r' || s[i] == '\n')) i++; }
        char Take() { Check(i < s.Length, "truncated JSON"); return s[i++]; }
        bool Eat(char c) { Ws(); if (i < s.Length && s[i] == c) { i++; return true; } return false; }
        object Value() { Ws(); Check(++depth <= 64 && i < s.Length, "invalid or deeply nested JSON"); char c = s[i]; object o;
            if (c == '{') o = Object(); else if (c == '[') o = Array(); else if (c == '"') o = String();
            else if (c == 't' && Token("true")) o = true; else if (c == 'f' && Token("false")) o = false;
            else if (c == 'n' && Token("null")) o = null; else o = Number(); depth--; return o; }
        bool Token(string t) { if (i + t.Length > s.Length || s.Substring(i, t.Length) != t) return false; i += t.Length; return true; }
        object Object() { Take(); var d = new Dictionary<string, object>(StringComparer.Ordinal); var seen = new HashSet<string>(CI); if (Eat('}')) return d;
            do { Ws(); Check(i < s.Length && s[i] == '"', "invalid JSON member"); string k = String(); Check(seen.Add(k), "duplicate JSON member"); Check(Eat(':'), "invalid JSON separator"); d.Add(k, Value()); if (Eat('}')) return d; Check(Eat(','), "invalid JSON object"); } while (true); }
        object Array() { Take(); var a = new List<object>(); if (Eat(']')) return a;
            do { Check(a.Count < MaxEntries * 4, "JSON array is too large"); a.Add(Value()); if (Eat(']')) return a; Check(Eat(','), "invalid JSON array"); } while (true); }
        string String() { Check(Take() == '"', "invalid JSON string"); StringBuilder b = new StringBuilder();
            while (true) { char c = Take(); if (c == '"') break; Check(c >= 32, "invalid JSON control");
                if (c != '\\') b.Append(c); else { c = Take(); if (c == '"' || c == '\\' || c == '/') b.Append(c); else if (c == 'b') b.Append('\b'); else if (c == 'f') b.Append('\f'); else if (c == 'n') b.Append('\n'); else if (c == 'r') b.Append('\r'); else if (c == 't') b.Append('\t'); else if (c == 'u') { Check(i + 4 <= s.Length, "truncated JSON escape"); ushort n; Check(UInt16.TryParse(s.Substring(i, 4), System.Globalization.NumberStyles.HexNumber, System.Globalization.CultureInfo.InvariantCulture, out n), "invalid JSON escape"); i += 4; b.Append((char)n); } else throw new InvalidDataException("invalid JSON escape"); } }
            string v = b.ToString(); for (int j=0; j<v.Length; j++) { if (Char.IsHighSurrogate(v[j])) { Check(j+1 < v.Length && Char.IsLowSurrogate(v[++j]), "invalid Unicode surrogate"); } else Check(!Char.IsLowSurrogate(v[j]), "invalid Unicode surrogate"); } return v; }
        object Number() { int start = i; if (i < s.Length && s[i] == '-') i++; Check(i < s.Length && s[i] >= '0' && s[i] <= '9', "invalid JSON value");
            if (s[i] == '0') i++; else while (i < s.Length && s[i] >= '0' && s[i] <= '9') i++; long n; Check(Int64.TryParse(s.Substring(start, i-start), System.Globalization.NumberStyles.AllowLeadingSign, System.Globalization.CultureInfo.InvariantCulture, out n), "JSON number out of range"); return n; }
    }

    static void Relative(string p, string root) {
        Check(!String.IsNullOrEmpty(p) && p[0] != '/' && p.IndexOf('\\') < 0 && p.IndexOf('\ufffd') < 0, "unsafe relative path");
        foreach (string c in p.Split('/')) {
            Check(c.Length > 0 && c != "." && c != ".." && c.Length <= 255 && !c.EndsWith(".") && !c.EndsWith(" "), "unsafe path component");
            foreach (char ch in c) Check(ch >= 32 && "<>:\"|?*".IndexOf(ch) < 0, "unsafe path character");
            string stem = c.Split('.')[0].TrimEnd(' '); Check(!Device.IsMatch(stem), "reserved Windows name");
        }
        Check((root + "\\" + p.Replace('/', '\\')).Length < 240, "Windows path is too long");
    }
    static void Provenance(Dictionary<string, object> p, string sha, string tree, string config) {
        Check(Str(Field(p,"source_sha")) == sha && Str(Field(p,"source_tree")) == tree, "source identity differs");
        Check(H40.IsMatch(Str(Field(p,"workflow_sha"))), "invalid workflow identity");
        object clean = Field(p,"source_clean"); Check(clean is bool && (bool)clean, "source was not clean");
        Check(Line(Field(p,"configuration")) == config, "configuration differs");
        foreach (string k in new string[]{"qt","sdk","windows_sdk","compiler","generator","runner_image"}) Line(Field(p,k));
        foreach (string k in new string[]{"conan_lock_sha256","conan_graph_sha256"}) Check(H64.IsMatch(Str(Field(p,k))), "invalid provenance digest");
        var subs = Obj(Field(p,"submodules")); Check(subs.Count > 0, "empty submodules"); foreach (var x in subs) Check(H40.IsMatch(Str(x.Value)), "invalid submodule identity");
        var tools = Arr(Field(p,"tools")); Check(tools.Count > 0, "empty tools"); var names = new HashSet<string>(CI);
        foreach (object item in tools) { var t = Obj(item); string name = Line(Field(t,"name")); Check(Regex.IsMatch(name, @"\A[a-z0-9._-]+\z") && names.Add(name), "invalid tool name"); Line(Field(t,"version"));
            Uri u; Check(Uri.TryCreate(Line(Field(t,"origin")), UriKind.Absolute, out u) && u.Scheme == Uri.UriSchemeHttps && u.Host.Length > 0 && u.UserInfo.Length == 0 && u.Query.Length == 0 && u.Fragment.Length == 0, "invalid tool origin"); Check(H64.IsMatch(Str(Field(t,"sha256"))), "invalid tool digest"); }
        foreach (string n in new string[]{"cmake","ctest","python","embedded-cpython","lrelease","lupdate","rcc","ifw","7z"}) Check(names.Contains(n), "missing runtime tool identity");
    }
    sealed class FileRecord { public string Name; public long Size; public string Sha; public long Mtime; }
    sealed class Model { public Dictionary<string,FileRecord> Files = new Dictionary<string,FileRecord>(CI); public Dictionary<string,string> Dirs = new Dictionary<string,string>(CI); public long Bytes; }
    static Model ReadModel(byte[] bytes, string root, string sha, string tree, string config) {
        var m = Obj(Json.Parse(bytes)); Check(Int(Field(m,"schema")) == 1, "unsupported manifest schema"); Check(Str(Field(m,"logical_root")) == root, "logical root differs"); Provenance(Obj(Field(m,"provenance")), sha, tree, config);
        var model = new Model(); var spelling = new Dictionary<string,string>(CI); var entries = Arr(Field(m,"files")); var dirs = Arr(Field(m,"directories")); Check(entries.Count > 0 && entries.Count + dirs.Count + 1 <= MaxEntries, "invalid number of manifest entries");
        foreach (object d in dirs) { string n = Str(d); Relative(n, root); AddSpelling(spelling, n); Check(!model.Dirs.ContainsKey(n), "duplicate directory"); model.Dirs.Add(n,n); }
        foreach (object item in entries) { var f = Obj(item); var r = new FileRecord(); r.Name = Str(Field(f,"path")); Relative(r.Name, root); AddSpelling(spelling,r.Name); r.Size = Int(Field(f,"bytes")); r.Sha = Str(Field(f,"sha256")); r.Mtime = Int(Field(f,"mtime_ns"));
            Check(r.Size >= 0 && r.Size <= MaxFile && model.Bytes <= MaxTotal - r.Size, "file size exceeds bound"); Check(H64.IsMatch(r.Sha), "invalid file digest"); Check(r.Mtime >= 0 && r.Mtime % 100 == 0 && r.Mtime / 100 <= DateTime.MaxValue.Ticks - 621355968000000000L, "mtime cannot be preserved exactly"); model.Bytes += r.Size;
            Check(!model.Files.ContainsKey(r.Name) && !model.Dirs.ContainsKey(r.Name) && !CI.Equals(r.Name, Manifest), "duplicate file or internal manifest"); model.Files.Add(r.Name,r); }
        Check(model.Dirs.ContainsKey("_bundle"), "bundle directory missing");
        foreach (string r in Required) Check(model.Files.ContainsKey(r) && model.Files[r].Name == r, "required interpreter or verifier input missing");
        foreach (string n in model.Dirs.Keys) ParentExists(n, model.Dirs);
        foreach (string n in model.Files.Keys) ParentExists(n, model.Dirs);
        return model;
    }
    static void AddSpelling(Dictionary<string,string> all, string name) { string[] parts = name.Split('/'); string p = ""; foreach (string c in parts) { p = p.Length == 0 ? c : p + "/" + c; string prior; if (all.TryGetValue(p, out prior)) Check(prior == p, "case-colliding paths"); else all.Add(p,p); } }
    static void ParentExists(string name, Dictionary<string,string> dirs) { int p = name.LastIndexOf('/'); if (p >= 0) { string parent = name.Substring(0,p); Check(dirs.ContainsKey(parent) && dirs[parent] == parent, "missing or mis-cased parent directory"); } }
    // Bound central-directory allocation before ZipArchive enumerates it.
    // Only a single-disk, comment-free canonical ZIP/ZIP64 is accepted.
    static byte[] At(Stream s, long offset, int length) { Check(offset>=0 && offset<=s.Length-length, "invalid ZIP offset"); s.Position=offset; byte[] b=new byte[length]; int n=0, k; while (n<length && (k=s.Read(b,n,length-n))>0) n+=k; Check(n==length, "truncated ZIP structure"); return b; }
    static ushort U16(byte[] b,int i) { return BitConverter.ToUInt16(b,i); }
    static uint U32(byte[] b,int i) { return BitConverter.ToUInt32(b,i); }
    static ulong U64(byte[] b,int i) { return BitConverter.ToUInt64(b,i); }
    static void ZipBounds(Stream s) {
        Check(BitConverter.IsLittleEndian && s.Length>=22, "invalid ZIP end record"); long end=s.Length-22; byte[] e=At(s,end,22);
        Check(U32(e,0)==0x06054b50 && U16(e,20)==0 && U16(e,4)==0 && U16(e,6)==0, "ZIP must be single-disk and comment-free");
        ulong diskCount=U16(e,8), count=U16(e,10), size=U32(e,12), start=U32(e,16), boundary=(ulong)end;
        bool zip64=diskCount==0xffff || count==0xffff || size==0xffffffff || start==0xffffffff || (end>=20 && U32(At(s,end-20,4),0)==0x07064b50);
        if (zip64) {
            Check(end>=76, "missing ZIP64 records"); byte[] loc=At(s,end-20,20);
            Check(U32(loc,0)==0x07064b50 && U32(loc,4)==0 && U32(loc,16)==1, "invalid ZIP64 locator"); ulong off=U64(loc,8); Check(off<=(ulong)(end-76), "invalid ZIP64 offset"); byte[] z=At(s,(long)off,56);
            Check(U32(z,0)==0x06064b50 && U64(z,4)==44 && off+56==(ulong)(end-20), "invalid ZIP64 end record");
            Check(U32(z,16)==0 && U32(z,20)==0, "multi-disk ZIP64 is unsupported"); ulong dc=U64(z,24), c=U64(z,32), sz=U64(z,40), st=U64(z,48);
            Check((diskCount==0xffff || diskCount==dc) && (count==0xffff || count==c) && (size==0xffffffff || size==sz) && (start==0xffffffff || start==st), "inconsistent ZIP64 records"); diskCount=dc; count=c; size=sz; start=st; boundary=off;
        }
        Check(count>0 && count<=MaxEntries && diskCount==count && size<=268435456UL && size>=count*46 && start<=boundary && size==boundary-start, "ZIP central directory exceeds bounds or is inconsistent");
        // Count central records ourselves before ZipArchive can allocate them;
        // a forged small EOCD count must not hide millions of records.
        ulong p=start; for (ulong i=0; i<count; i++) {
            Check(p<=boundary && boundary-p>=46, "truncated ZIP central record"); byte[] h=At(s,(long)p,46);
            Check(U32(h,0)==0x02014b50 && (U16(h,8) & 0x2041)==0 && (U16(h,10)==0 || U16(h,10)==8), "unsupported or encrypted ZIP entry");
            ulong name=U16(h,28), extra=U16(h,30), comment=U16(h,32); Check(name>0 && name<=720, "ZIP entry name exceeds bound");
            ulong length=46+name+extra+comment; Check(length<=boundary-p, "truncated ZIP central record"); p+=length;
        }
        Check(p==boundary, "ZIP central entry count differs");
    }
    static Dictionary<string,ZipArchiveEntry> Members(ZipArchive z, string root) {
        Check(z.Entries.Count > 0 && z.Entries.Count <= MaxEntries, "invalid ZIP entry count"); var result = new Dictionary<string,ZipArchiveEntry>(CI); var spell = new Dictionary<string,string>(CI); long total = 0;
        foreach (ZipArchiveEntry e in z.Entries) { string raw = e.FullName; bool dir = raw.EndsWith("/", StringComparison.Ordinal); string n = dir ? raw.Substring(0,raw.Length-1) : raw; Relative(n,root); AddSpelling(spell,n);
            Check(!result.ContainsKey(n), "duplicate or colliding ZIP member"); uint attr = unchecked((uint)e.ExternalAttributes); uint mode = (attr >> 16) & 0xf000; Check((attr & 0xffff & ~0x37u) == 0, "unsafe ZIP attributes");
            Check(mode == 0 || mode == (dir ? 0x4000u : 0x8000u), "nonregular ZIP entry"); Check((attr & 0x10) == 0 || dir, "inconsistent ZIP directory attribute");
            Check(e.Length >= 0 && e.Length <= MaxFile && e.CompressedLength >= 0 && e.CompressedLength <= MaxArchive && total <= MaxTotal - e.Length, "ZIP size exceeds bound"); if (dir) Check(e.Length == 0, "directory ZIP member is not empty"); total += e.Length; result.Add(n,e); }
        return result;
    }
    static byte[] ReadSmall(ZipArchiveEntry e) { Check(e.Length >= 0 && e.Length <= MaxManifest, "manifest exceeds bound"); using (Stream s=e.Open()) using (var b=new MemoryStream()) { byte[] buf=new byte[65536]; long n=0; int k; while ((k=s.Read(buf,0,buf.Length)) != 0) { n += k; Check(n <= e.Length && n <= MaxManifest, "manifest length differs"); b.Write(buf,0,k); } Check(n==e.Length,"manifest length differs"); return b.ToArray(); } }
    static void MatchMembers(Model m, Dictionary<string,ZipArchiveEntry> z) {
        Check(z.Count == m.Files.Count + m.Dirs.Count + 1, "ZIP has missing or extra entries");
        foreach (var d in m.Dirs) { ZipArchiveEntry e; Check(z.TryGetValue(d.Key,out e) && e.FullName == d.Value + "/", "missing or mis-cased ZIP directory"); }
        foreach (var f in m.Files) { ZipArchiveEntry e; Check(z.TryGetValue(f.Key,out e) && e.FullName == f.Value.Name && e.Length == f.Value.Size, "missing, mis-cased or wrong-size ZIP file"); }
        ZipArchiveEntry manifest; Check(z.TryGetValue(Manifest,out manifest) && manifest.FullName == Manifest, "internal manifest missing");
    }

    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct StreamData { public long Size; [MarshalAs(UnmanagedType.ByValTStr, SizeConst=296)] public string Name; }
    [StructLayout(LayoutKind.Sequential)] struct BY_HANDLE_FILE_INFORMATION { public uint Attributes; public System.Runtime.InteropServices.ComTypes.FILETIME Creation, Access, Write; public uint VolumeSerial, SizeHigh, SizeLow, Links, IndexHigh, IndexLow; }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr FindFirstStreamW(string path, int info, out StreamData data, uint flags);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool FindNextStreamW(IntPtr handle, out StreamData data);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool FindClose(IntPtr handle);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern uint GetFileAttributesW(string path);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool CreateDirectoryW(string path, IntPtr security);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern SafeFileHandle CreateFileW(string path, uint access, uint share, IntPtr sec, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle, StringBuilder path, uint length, uint flags);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetFileInformationByHandle(SafeFileHandle handle, out BY_HANDLE_FILE_INFORMATION info);
    static void Streams(string path, bool directory) {
        StreamData data; IntPtr h = FindFirstStreamW(path,0,out data,0); if (h == new IntPtr(-1)) { int err=Marshal.GetLastWin32Error(); Check(directory && err==38, "cannot enumerate required Windows data streams"); return; }
        int count=0; try { do { count++; Check(!directory && data.Name == "::$DATA" && count == 1, "named or unexpected data stream"); } while (FindNextStreamW(h,out data)); Check(Marshal.GetLastWin32Error()==38, "data stream enumeration failed"); Check(directory || count==1, "unnamed file stream missing"); } finally { Check(FindClose(h), "stream enumeration close failed"); }
    }
    static uint Attributes(string p) { uint a=GetFileAttributesW(p); Check(a != 0xffffffff, "cannot inspect filesystem path"); Check((a & 0x400) == 0, "reparse point or symlink"); return a; }
    static SafeFileHandle LockDirectory(string path) {
        uint a=Attributes(path); Check((a & 0x10) != 0, "expected ordinary directory");
        SafeFileHandle h=CreateFileW(path,0x80000000,3,IntPtr.Zero,3,0x02200000,IntPtr.Zero); Check(!h.IsInvalid, "cannot lock directory");
        try { BY_HANDLE_FILE_INFORMATION info; Check(GetFileInformationByHandle(h,out info) && (info.Attributes & 0x410) == 0x10, "directory is a reparse point or not a directory"); var b=new StringBuilder(32768); uint n=GetFinalPathNameByHandleW(h,b,(uint)b.Capacity,0); Check(n>0 && n<b.Capacity && String.Equals(b.ToString(), @"\\?\" + path, StringComparison.OrdinalIgnoreCase), "directory path is an alias"); Streams(path,true); return h; } catch { h.Dispose(); throw; }
    }
    static void FileHandleCheck(FileStream s, string path) { BY_HANDLE_FILE_INFORMATION i; Check(GetFileInformationByHandle(s.SafeFileHandle,out i) && (i.Attributes & (0x400|0x10)) == 0 && i.Links == 1, "file is not ordinary or has hard links"); Streams(path,false); }
    static void ArchiveIdentity(FileStream stream, string path) {
        uint a=Attributes(path); Check((a & 0x10)==0, "archive is not an ordinary file"); FileHandleCheck(stream,path);
        for (string p=Path.GetDirectoryName(path); p!=null; p=Path.GetDirectoryName(p)) Check((Attributes(p) & 0x10)!=0, "archive ancestry is not an ordinary directory");
        var b=new StringBuilder(32768); uint n=GetFinalPathNameByHandleW(stream.SafeFileHandle,b,(uint)b.Capacity,0); Check(n>0 && n<b.Capacity && String.Equals(b.ToString(), @"\\?\" + path, StringComparison.OrdinalIgnoreCase), "archive path is an alias");
    }
    static string DiskPath(string root, string name) { return root + "\\" + name.Replace('/','\\'); }
    static void NewDir(string p, List<SafeFileHandle> held) { Check(CreateDirectoryW(p,IntPtr.Zero), "destination already exists or directory creation failed"); held.Add(LockDirectory(p)); }
    static void RootDirectories(string root, List<SafeFileHandle> held) {
        Check(new DriveInfo("C").DriveType == DriveType.Fixed, "destination drive is not fixed");
        string[] p={@"C:\", @"C:\Users", @"C:\Users\Administrator", @"C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a", @"C:\Users\Administrator\PlotJuggler-4.1.0-zh-test-558a\n"};
        foreach (string d in p) { uint a=GetFileAttributesW(d); if (a==0xffffffff) { int e=Marshal.GetLastWin32Error(); Check(e==2 || e==3, "cannot inspect destination ancestry"); NewDir(d,held); } else held.Add(LockDirectory(d)); }
        // CreateDirectory, not Exists, is the atomic no-reuse check. Distinguish
        // a preexisting target from other creation failures in the receipt path.
        if (!CreateDirectoryW(root,IntPtr.Zero)) { int error=Marshal.GetLastWin32Error();
            Check(error!=183 && error!=80, "destination already exists"); throw new InvalidDataException("destination directory creation failed"); }
        held.Add(LockDirectory(root));
    }
    static string ExtractFile(ZipArchiveEntry e, string target, long expected) {
        long count=0; byte[] b=new byte[1024*1024]; using (Stream input=e.Open()) using (FileStream output=new FileStream(target,FileMode.CreateNew,FileAccess.Write,FileShare.None)) using (SHA256 h=SHA256.Create()) {
            int n; while ((n=input.Read(b,0,b.Length)) != 0) { Check(count <= expected-n, "decompressed data exceeds expected length"); count += n; output.Write(b,0,n); h.TransformBlock(b,0,n,b,0); } h.TransformFinalBlock(new byte[0],0,0); output.Flush(true); Check(count==expected, "decompressed size differs"); return Hex(h.Hash); }
    }
    static void VerifyFile(string p, long size, string sha, long? mtime) { Attributes(p); using (var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.Read)) { FileHandleCheck(f,p); Check(f.Length == size && Hash(f) == sha, "extracted file does not match manifest"); if (mtime.HasValue) Check(File.GetLastWriteTimeUtc(p).Ticks == 621355968000000000L + mtime.Value/100, "original timestamp could not be restored exactly"); } }
    static void Walk(string root, string relative, Model m, ref int files, ref int dirs) {
        string path = relative.Length == 0 ? root : DiskPath(root,relative); Streams(path,true);
        foreach (string full in Directory.GetFileSystemEntries(path)) { string name=Path.GetFileName(full); string r=relative.Length==0?name:relative+"/"+name; Relative(r,root); uint a=Attributes(full);
            if ((a & 0x10)!=0) { string expected; Check(m.Dirs.TryGetValue(r,out expected) && expected==r, "unexpected or mis-cased extracted directory"); dirs++; Walk(root,r,m,ref files,ref dirs); }
            else { FileRecord record; if (r == Manifest) { files++; continue; } Check(m.Files.TryGetValue(r,out record) && record.Name==r, "unexpected or mis-cased extracted file"); files++; }
        }
    }
    static void VerifyOrigins(string root, Model m) {
        string path=DiskPath(root,Origins); var rec=m.Files[Origins]; Check(rec.Size<=MaxManifest, "origin record exceeds bound"); byte[] data; using (var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)) { FileHandleCheck(stream,path); Check(stream.Length==rec.Size, "origin record size differs"); data=new byte[(int)rec.Size]; int off=0, n; while (off<data.Length && (n=stream.Read(data,off,data.Length-off))>0) off+=n; Check(off==data.Length && Hash(data)==rec.Sha, "origin record hash differs"); } var d=Obj(Json.Parse(data)); Check(Int(Field(d,"schema"))==1,"invalid origin record"); var origins=Obj(Field(d,"origins")); Check(origins.Count>0,"empty origins");
        foreach (var origin in origins) { var value=Obj(origin.Value); var list=Arr(Field(value,"license_files")); Check(list.Count>0,"origin has no license"); foreach (object item in list) { string p=Str(item); Relative(p,root); FileRecord record; Check(m.Files.TryGetValue(p,out record) && record.Name==p,"origin license is not in verified payload"); } }
    }
    // CPython reads the path file before any launcher code. Verify its exact
    // import-search contract from authenticated bytes without starting Python.
    static void ValidateInterpreterPathBytes(byte[] data, string root, Model model) {
        Check(data.Length > 0 && data.Length < 32768, "interpreter path file size is invalid");
        string text; try { text = new UTF8Encoding(false,true).GetString(data); }
        catch (DecoderFallbackException) { throw new InvalidDataException("interpreter path file is not strict UTF-8"); }
        for (int i=0; i<text.Length; i++) { char c=text[i];
            Check(c != '\0' && (c>=32 || c=='\n' || c=='\r' || c=='\t'), "interpreter path file has a control character");
            if (c=='\r') Check(i+1<text.Length && text[i+1]=='\n', "interpreter path file has an unsupported line ending"); }
        foreach (string d in new string[]{"t/python","s","s/scripts","s/tests","s/packaging/localization"}) {
            string actual; Check(model.Dirs.TryGetValue(d,out actual) && actual==d, "interpreter search directory is not in the manifest");
        }
        string py=Path.Combine(root,@"t\python");
        string[] expected={Path.Combine(py,"python312.zip"),py,Path.Combine(root,"s"),Path.Combine(root,@"s\scripts"),Path.Combine(root,@"s\tests"),Path.Combine(root,@"s\packaging\localization")};
        int count=0;
        foreach (string original in text.Replace("\r\n","\n").Split('\n')) {
            int comment=original.IndexOf('#'); string line=(comment<0 ? original : original.Substring(0,comment)).Trim(' ','\t');
            if (line.Length==0) continue;
            Check(!Regex.IsMatch(line,@"\Aimport(?:\s|\z)",RegexOptions.IgnoreCase | RegexOptions.CultureInvariant), "interpreter path file contains an import directive");
            Check(count<expected.Length && line.IndexOfAny(new char[]{'<','>','\"','|','?','*','~'})<0, "interpreter path entry is unsafe or extra");
            bool absolute=Regex.IsMatch(line,@"\A[A-Za-z]:[\\/]");
            if (absolute) Check(line.IndexOf(':',2)<0, "interpreter path entry has an alternate stream");
            else Check(line.IndexOf(':')<0 && line[0]!='\\' && line[0]!='/', "interpreter path entry is not a safe relative path");
            foreach (string part in line.Replace('/','\\').Split('\\'))
                if (part.Length>0 && part!="." && part!=".." && !part.EndsWith(":"))
                    Check(!part.EndsWith(".") && !part.EndsWith(" ") && !Device.IsMatch(part.Split('.')[0].TrimEnd(' ')), "interpreter path has an ambiguous component");
            string resolved=Path.GetFullPath(absolute ? line : Path.Combine(py,line)).TrimEnd('\\');
            Check(String.Equals(resolved,Path.GetFullPath(expected[count]).TrimEnd('\\'),StringComparison.OrdinalIgnoreCase), "interpreter path entry differs from the allowlist");
            count++;
        }
        Check(count==expected.Length, "interpreter path file is missing an allowlisted entry");
    }
    static void VerifyInterpreterPathFile(string root, Model model) {
        const string relative="t/python/python312._pth"; FileRecord rec;
        Check(model.Files.TryGetValue(relative,out rec) && rec.Name==relative && rec.Size>0 && rec.Size<32768, "authenticated interpreter path file missing or oversized");
        string path=DiskPath(root,relative); byte[] bytes;
        using (var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)) {
            FileHandleCheck(stream,path); Check(stream.Length==rec.Size, "interpreter path file size differs");
            bytes=new byte[(int)rec.Size]; int offset=0,n; while (offset<bytes.Length && (n=stream.Read(bytes,offset,bytes.Length-offset))>0) offset+=n;
            Check(offset==bytes.Length && Hash(bytes)==rec.Sha, "interpreter path file hash differs");
        }
        ValidateInterpreterPathBytes(bytes,root,model);
    }
    public static string Run(string archive, string archiveSha, string manifestSha, string sha, string tree, string config, string temp) {
        Check(H64.IsMatch(archiveSha) && H64.IsMatch(manifestSha) && H40.IsMatch(sha) && H40.IsMatch(tree), "independent hashes must be full lower-case hex"); Check(config == "RelWithDebInfo", "unexpected build configuration");
        string root=Base+sha.Substring(0,12); string source=Path.GetFullPath(archive); Check(Regex.IsMatch(source,@"\A[A-Za-z]:\\[^:]*\z") && !source.StartsWith(@"\\?\"), "archive path must be an ordinary local path");
        List<SafeFileHandle> held=new List<SafeFileHandle>();
        try { using (var f=new FileStream(source,FileMode.Open,FileAccess.Read,FileShare.Read)) { ArchiveIdentity(f,source); Check(f.Length>0 && f.Length<=MaxArchive, "archive size exceeds bound"); Check(Hash(f)==archiveSha, "archive SHA-256 differs from independent evidence"); ZipBounds(f); f.Position=0;
            using (var zip=new ZipArchive(f,ZipArchiveMode.Read,true)) { var members=Members(zip,root); ZipArchiveEntry me; Check(members.TryGetValue(Manifest,out me) && me.FullName==Manifest,"internal manifest missing"); byte[] manifest=ReadSmall(me); Check(Hash(manifest)==manifestSha, "manifest SHA-256 differs from independent evidence"); Model model=ReadModel(manifest,root,sha,tree,config); MatchMembers(model,members);
                Check(new DriveInfo("C").AvailableFreeSpace >= model.Bytes + manifest.Length + Reserve, "insufficient free space including reserve");
                RootDirectories(root,held); var dirs=new List<string>(model.Dirs.Values); dirs.Sort(delegate(string a,string b) { int c=a.Split('/').Length.CompareTo(b.Split('/').Length); return c!=0?c:StringComparer.Ordinal.Compare(a,b); }); foreach (string d in dirs) NewDir(DiskPath(root,d),held);
                foreach (FileRecord record in model.Files.Values) { Check(new DriveInfo("C").AvailableFreeSpace >= record.Size + Reserve, "free space fell below reserve"); string p=DiskPath(root,record.Name); Check(ExtractFile(members[record.Name],p,record.Size)==record.Sha, "ZIP file hash differs"); }
                Check(new DriveInfo("C").AvailableFreeSpace >= manifest.Length + Reserve, "free space fell below reserve"); string manifestPath=DiskPath(root,Manifest); Check(ExtractFile(me,manifestPath,manifest.Length)==manifestSha, "extracted manifest hash differs");
                foreach (FileRecord record in model.Files.Values) VerifyFile(DiskPath(root,record.Name),record.Size,record.Sha,null);
                VerifyFile(manifestPath,manifest.Length,manifestSha,null); VerifyInterpreterPathFile(root,model); VerifyOrigins(root,model);
                int fileCount=0,dirCount=0; Walk(root,"",model,ref fileCount,ref dirCount); Check(fileCount==model.Files.Count+1 && dirCount==model.Dirs.Count, "extracted inventory differs");
                // Restore only original authenticated values after all bytes and identity passed.
                foreach (FileRecord record in model.Files.Values) File.SetLastWriteTimeUtc(DiskPath(root,record.Name),new DateTime(621355968000000000L+record.Mtime/100,DateTimeKind.Utc));
                foreach (FileRecord record in model.Files.Values) VerifyFile(DiskPath(root,record.Name),record.Size,record.Sha,record.Mtime); VerifyFile(manifestPath,manifest.Length,manifestSha,null); VerifyInterpreterPathFile(root,model); VerifyOrigins(root,model); fileCount=0; dirCount=0; Walk(root,"",model,ref fileCount,ref dirCount); Check(fileCount==model.Files.Count+1 && dirCount==model.Dirs.Count, "final inventory differs");
                return "{\"schema\":1,\"status\":\"verified\",\"archive_sha256\":\""+archiveSha+"\",\"manifest_sha256\":\""+manifestSha+"\",\"source_sha\":\""+sha+"\",\"source_tree\":\""+tree+"\",\"configuration\":\""+config+"\",\"logical_root\":\""+root.Replace("\\","\\\\")+"\",\"bootstrap_temp\":\""+temp.Replace("\\","\\\\")+"\",\"files\":"+model.Files.Count+",\"directories\":"+model.Dirs.Count+",\"bytes\":"+model.Bytes+",\"named_streams\":\"checked\",\"interpreter_path_file\":\"authenticated_and_allowlisted\",\"mtimes\":\"verified_manifest_values_restored\",\"kit_code_executed\":false}";
            } }
        } finally { for (int i=held.Count-1;i>=0;i--) held[i].Dispose(); }
    }
}
'@
    $compilerParameters = New-Object System.CodeDom.Compiler.CompilerParameters
    $compilerParameters.GenerateInMemory = $true
    $compilerParameters.IncludeDebugInformation = $false
    $compilerParameters.TempFiles = [System.CodeDom.Compiler.TempFileCollection]::new($TrustedTemp, $true)
    foreach ($assembly in $assemblies) { [void]$compilerParameters.ReferencedAssemblies.Add($assembly.Location) }
    Add-Type -TypeDefinition $code -CompilerParameters $compilerParameters
    $receipt = [NativeKitBootstrap]::Run($Archive, $ArchiveSha256, $ManifestSha256, $SourceSha, $SourceTree, $Configuration, $TrustedTemp)
    [Console]::Out.WriteLine($receipt)
    exit 0
} catch {
    [Console]::Error.WriteLine('Native kit bootstrap failed: ' + $_.Exception.GetBaseException().Message)
    exit 1
}
