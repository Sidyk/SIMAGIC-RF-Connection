// Tested host-side experiment only: Alpha U VID 0483/PID 0522, NEO X 1.0.9.
// Requires HidSharp.dll at build time. No vendor assembly is redistributed.
// See docs/reproduction.md. Never use a profile captured from another wheel.
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using HidSharp;

internal static class HidReproducer {
    const int Length = 241;
    static string captureDir, frameDir, devicePath;

    static int Main(string[] args) {
        try {
            if (args.Length == 1 && String.Equals(args[0], "list", StringComparison.OrdinalIgnoreCase)) {
                ListDevices(); return 0;
            }
            if (args.Length < 3) { Usage(); return 2; }
            string command = args[0].ToLowerInvariant();
            devicePath = args[1]; captureDir = Path.GetFullPath(args[2]);
            if (command == "capture" && args.Length == 3) Capture();
            else if (command == "test" && args.Length == 5 && args[4] == "--send") {
                frameDir = Path.GetFullPath(args[3]); Test();
            }
            else if (command == "recover" && args.Length == 3) Recover();
            else { Usage(); return 2; }
            return 0;
        } catch (Exception e) {
            Console.Error.WriteLine("STOP: " + e.Message);
            return 1;
        }
    }

    static void Usage() {
        Console.WriteLine("HidReproducer list");
        Console.WriteLine("HidReproducer capture <exact-HID-device-path> <private-dir>");
        Console.WriteLine("HidReproducer test <exact-HID-device-path> <private-dir> <frames-dir> --send");
        Console.WriteLine("HidReproducer recover <exact-HID-device-path> <private-dir>");
        Console.WriteLine("test sends LED commands; capture only reads configuration; recover requires a pending journal.");
    }

    static string InCapture(string name) { return Path.Combine(captureDir, name); }
    static string InFrames(string name) { return Path.Combine(frameDir, name); }
    static string InRecovery(string name) { return Path.Combine(InCapture("recovery"), name); }
    static string PendingPath { get { return InCapture("restore.pending"); } }

    static void ListDevices() {
        HidDevice[] devices = DeviceList.Local.GetHidDevices(0x0483, 0x0522).ToArray();
        if (devices.Length == 0) Console.WriteLine("No matching base HID interface found.");
        foreach (HidDevice d in devices)
            Console.WriteLine("Feature length " + d.GetMaxFeatureReportLength() + " | " + d.DevicePath);
        Console.WriteLine("A matching VID/PID/path does not prove that an RF wheel is connected.");
    }

    static void NoCompetingOwner() {
        foreach (string name in new string[] { "simpro", "simpro3", "SimHubWPF" }) {
            Process[] processes = Process.GetProcessesByName(name);
            try { if (processes.Length != 0) throw new InvalidOperationException(name + " is still running; exit it before HID access"); }
            finally { foreach (Process p in processes) p.Dispose(); }
        }
    }

    static HidDevice ExactDevice() {
        if (String.IsNullOrWhiteSpace(devicePath)) throw new ArgumentException("An exact HID device path is required");
        HidDevice[] matches = DeviceList.Local.GetHidDevices(0x0483, 0x0522)
            .Where(d => String.Equals(d.DevicePath, devicePath, StringComparison.OrdinalIgnoreCase)
                        && d.GetMaxFeatureReportLength() == Length).ToArray();
        if (matches.Length != 1) throw new IOException("Expected exactly one saved Alpha U HID interface with 241-byte feature reports");
        return matches[0];
    }

    static void ValidateRaw(byte[] raw) {
        if (raw.Length != Length || raw[0] != 0x90 || raw[235] != 9)
            throw new InvalidDataException("Expected 241-byte 0x90 readback with tested firmware indicator 9");
    }

    static bool EqualRange(byte[] a, byte[] b, int first, int lastInclusive) {
        for (int i = first; i <= lastInclusive; i++) if (a[i] != b[i]) return false;
        return true;
    }

    static byte[] ReadRaw(HidStream stream) {
        NoCompetingOwner();
        byte[] request = new byte[Length]; request[0] = 0x80; request[1] = 5; request[2] = 0xBB; request[3] = 0xBB;
        stream.SetFeature(request);
        Thread.Sleep(200);
        byte[] raw = new byte[Length]; raw[0] = 0x90;
        stream.GetFeature(raw);
        ValidateRaw(raw);
        return raw;
    }

    static void Send(HidStream stream, byte[] report) {
        NoCompetingOwner();
        if (report == null || report.Length != Length) throw new InvalidDataException("Report must be exactly 241 bytes");
        stream.SetFeature(report);
    }

    static byte[] ConfigPart(string path, int number) {
        byte[] p = File.ReadAllBytes(path);
        if (p.Length != Length || p[0] != 0x91 || p[1] != number)
            throw new InvalidDataException("Invalid configuration part " + number + ": " + path);
        for (int i = 62; i < Length; i++) if (p[i] != 0) throw new InvalidDataException("Nonzero configuration padding");
        if (number == 3) for (int i = 56; i < 62; i++) if (p[i] != 0) throw new InvalidDataException("Readback firmware bytes copied into write");
        return p;
    }

    static byte[] Telemetry(string path) {
        byte[] p = File.ReadAllBytes(path);
        if (p.Length != Length || p[0] != 0x91 || p[1] != 4)
            throw new InvalidDataException("Invalid telemetry report: " + path);
        return p;
    }

    static byte[] ExpectedTelemetry(int row, int rpm, int percent, int flag) {
        byte[] p = new byte[Length]; p[0] = 0x91; p[1] = 4;
        p[3] = (byte)(rpm >> 8); p[4] = (byte)rpm;
        p[5] = (byte)(row << 4); p[6] = 0x10;
        p[14] = (byte)percent; p[16] = (byte)flag;
        return p;
    }

    static byte[][] Parts(string directory, string prefix) {
        byte[][] result = new byte[4][];
        for (int i = 0; i < 4; i++) result[i] = ConfigPart(Path.Combine(directory, prefix + "-config-" + i + ".bin"), i);
        return result;
    }

    static byte[] Reconstruct(byte[][] parts) {
        byte[] result = new byte[Length]; result[0] = 0x90; result[235] = 9;
        for (int part = 0; part < 4; part++) for (int i = 0; i < 60; i++) {
            int source = 1 + part * 60 + i;
            if (source <= 234) result[source] = parts[part][2 + i];
        }
        return result;
    }

    static void VerifyOriginal(byte[] raw, byte[][] parts) {
        byte[] c = Reconstruct(parts);
        if (!EqualRange(c, raw, 1, 50) || !EqualRange(c, raw, 231, 233))
            throw new InvalidDataException("Original reports changed mappings, thresholds, brightness or clutch");
        // Observed 0x90 response is a sampled view, not a complete LED readback.
        for (int group = 0; group < 2; group++) for (int i = 0; i < 5; i++)
            if (raw[51 + group * 5 + i] != c[51 + group * 5])
                throw new InvalidDataException("Original button report does not fit sampled readback");
        for (int led = 0; led < 9; led++) for (int group = 0; group < 2; group++)
            for (int i = 0; i < 5; i++)
                if (raw[81 + led * 10 + group * 5 + i] != c[81 + led * 10 + group * 5])
                    throw new InvalidDataException("Original RPM report does not fit sampled readback");
    }

    static void SendParts(HidStream stream, byte[][] parts) {
        for (int i = 0; i < 4; i++) Send(stream, parts[i]);
    }

    static void Capture() {
        NoCompetingOwner();
        if (File.Exists(PendingPath) || File.Exists(InCapture("readback.bin")))
            throw new IOException("Capture already exists or recovery is pending; use a fresh private directory");
        HidDevice device = ExactDevice();
        byte[] raw;
        using (HidStream stream = device.Open()) {
            stream.ReadTimeout = 1000; stream.WriteTimeout = 1000;
            raw = ReadRaw(stream);
            byte[] repeated = ReadRaw(stream);
            if (!EqualRange(raw, repeated, 1, 234)) throw new IOException("Two readbacks differ; no baseline saved");
        }
        Directory.CreateDirectory(captureDir);
        File.WriteAllBytes(InCapture("readback.bin"), raw);
        File.WriteAllText(InCapture("device-path.txt"), devicePath);
        Console.WriteLine("Saved private readback. No LED configuration or telemetry was sent.");
    }

    static void CheckSavedIdentity() {
        string savedPath = File.ReadAllText(InCapture("device-path.txt")).Trim();
        if (!String.Equals(savedPath, devicePath, StringComparison.OrdinalIgnoreCase))
            throw new IOException("This capture belongs to a different HID device path");
    }

    static void Test() {
        NoCompetingOwner(); CheckSavedIdentity();
        if (File.Exists(PendingPath)) throw new IOException("Restoration pending; run recover before another test");
        byte[] original = File.ReadAllBytes(InCapture("readback.bin")); ValidateRaw(original);
        byte[][] originalParts = Parts(frameDir, "original");
        byte[][] testParts = Parts(frameDir, "yellow-flag-button-1");
        VerifyOriginal(original, originalParts);
        byte[] a = Telemetry(InFrames("telemetry-stage-9.bin"));
        byte[] b = Telemetry(InFrames("telemetry-stage-4-yellow-flag.bin"));
        byte[] c = Telemetry(InFrames("telemetry-stage-0-yellow-flag.bin"));
        byte[] idle = Telemetry(InFrames("telemetry-idle.bin"));
        byte[] baselineConfig = Reconstruct(originalParts), testConfig = Reconstruct(testParts);
        if (!EqualRange(baselineConfig, testConfig, 1, 54) || !EqualRange(baselineConfig, testConfig, 56, 234)
            || testConfig[55] != 0x35)
            throw new InvalidDataException("Test configuration must change only logical button 1 to yellow FLAG");
        if (!a.SequenceEqual(ExpectedTelemetry(9, 6000, 76, 0))
            || !b.SequenceEqual(ExpectedTelemetry(4, 7000, 88, 3))
            || !c.SequenceEqual(ExpectedTelemetry(0, 8000, 99, 3))
            || !idle.SequenceEqual(ExpectedTelemetry(10, 0, 0, 0)))
            throw new InvalidDataException("Unexpected stage/FLAG test vectors");
        HidDevice device = ExactDevice();
        using (HidStream stream = device.Open()) {
            stream.ReadTimeout = 1000; stream.WriteTimeout = 1000;
            byte[] current = ReadRaw(stream), repeated = ReadRaw(stream);
            if (!EqualRange(current, repeated, 1, 234) || !EqualRange(current, original, 1, 234))
                throw new IOException("Base no longer matches captured original; no test writes sent");
            Directory.CreateDirectory(InCapture("recovery"));
            for (int i = 0; i < 4; i++) File.WriteAllBytes(InRecovery("original-config-" + i + ".bin"), originalParts[i]);
            File.WriteAllBytes(InRecovery("telemetry-idle.bin"), idle);
            File.WriteAllText(PendingPath, "Original configuration must be restored and verified before clearing this marker.");
            try {
                SendParts(stream, testParts);
                Phase(stream, a, "stage 9: first RPM level");
                Phase(stream, b, "stage 4: middle RPM + yellow FLAG");
                Phase(stream, c, "stage 0: redline + yellow FLAG");
            } finally {
                try { RestoreOnStream(stream, original); }
                catch (Exception e) { Console.Error.WriteLine("RECOVERY PENDING: " + e.Message); throw; }
            }
        }
        Console.WriteLine("Test finished; original readback verified. Check physical LEDs separately.");
    }

    static void Phase(HidStream stream, byte[] report, string title) {
        Console.WriteLine(title);
        Stopwatch timer = Stopwatch.StartNew();
        while (timer.ElapsedMilliseconds < 4000) {
            Send(stream, report);
            Thread.Sleep(50);
        }
    }

    static void Recover() {
        NoCompetingOwner(); CheckSavedIdentity();
        if (!File.Exists(PendingPath)) throw new IOException("No pending recovery marker");
        byte[] original = File.ReadAllBytes(InCapture("readback.bin")); ValidateRaw(original);
        HidDevice device = ExactDevice();
        using (HidStream stream = device.Open()) {
            stream.ReadTimeout = 1000; stream.WriteTimeout = 1000;
            RestoreOnStream(stream, original);
        }
        Console.WriteLine("Original readback verified; recovery marker cleared.");
    }

    static void RestoreOnStream(HidStream stream, byte[] original) {
        if (!File.Exists(PendingPath)) throw new IOException("No durable recovery marker");
        byte[] current = ReadRaw(stream);
        if (!EqualRange(current, original, 1, 50) || !EqualRange(current, original, 232, 233))
            throw new IOException("Mapping, thresholds or clutch changed; original was NOT overwritten");
        byte[][] parts = Parts(InCapture("recovery"), "original");
        VerifyOriginal(original, parts);
        byte[] idle = Telemetry(InRecovery("telemetry-idle.bin"));
        Send(stream, idle);
        SendParts(stream, parts);
        Thread.Sleep(1000);
        Send(stream, idle);
        byte[] after = ReadRaw(stream);
        if (!EqualRange(after, original, 1, 234))
            throw new IOException("Writable readback differs; keep the recovery marker and inspect wheel state");
        File.Delete(PendingPath);
    }
}
