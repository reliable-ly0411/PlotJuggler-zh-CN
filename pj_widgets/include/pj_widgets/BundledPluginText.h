// SPDX-License-Identifier: MPL-2.0
#pragma once
#include <QCoreApplication>
#include <QString>
namespace PJ {
// Presentation only. Manifest IDs, names used as legacy identities, and versions remain raw.
inline QString bundledPluginText(const QString& id, const QString& version, const QString& source) {
  struct Entry {
    const char* id;
    const char* version;
    const char* source;
  };
  static constexpr Entry entries[] = {
      {"toolbox-fft", "1.0.1", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Fast Fourier Transform")},
      {"toolbox-fft", "1.0.1",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata", "Compute the frequency-domain amplitude of numeric time series using FFT.")},
      {"arrow-parser", "1.0.0", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Arrow IPC Parser")},
      {"arrow-parser", "1.0.0",
       QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Message parser for self-describing Arrow IPC streams.")},
      {"csv-loader", "1.0.7", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "CSV Loader")},
      {"csv-loader", "1.0.7", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Data loader for CSV files.")},
      {"data-tamer-parser", "0.9.2", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "DataTamer Parser")},
      {"data-tamer-parser", "0.9.2",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Message parser for DataTamer encoded data. Efficient serialization for robotics.")},
      {"dummy-streamer", "1.0.1", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Dummy Streamer")},
      {"dummy-streamer", "1.0.1",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Generates synthetic sine, cosine, sawtooth, and noise signals for testing and demonstration.")},
      {"foxglove-bridge", "1.1.0", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Foxglove Bridge")},
      {"foxglove-bridge", "1.1.0",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Connect to Foxglove WebSocket server for ROS data streaming. Compatible with Foxglove Studio.")},
      {"json-parser", "1.3.0", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "JSON Parser")},
      {"json-parser", "1.3.0",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata", "Message parser for JSON, CBOR, MessagePack, and BSON encoded data.")},
      {"mcap-loader", "1.3.0", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "MCAP Loader")},
      {"mcap-loader", "1.3.0",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Data loader for MCAP files and split ROS 2 bags (metadata.yaml). Supports ROS1, ROS2, Protobuf, and JSON "
           "message encodings.")},
      {"mp4-loader", "0.10.0", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "MP4 Loader")},
      {"mp4-loader", "0.10.0",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Data loader for .mp4 video files. Reads the container's creation_time tag (when present) so the host can "
           "anchor the video on a wall-clock timeline; supports multi-file selection via the standard File dialog.")},
      {"parquet-loader", "1.0.2", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Parquet Loader")},
      {"parquet-loader", "1.0.2",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata", "Data loader for Apache Parquet files. Efficient columnar storage format.")},
      {"plotjuggler-bridge", "1.0.1", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "PlotJuggler Bridge")},
      {"plotjuggler-bridge", "1.0.1",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Connect to PlotJuggler Bridge server for generic data streaming over WebSocket.")},
      {"pointcloud-3d-loader", "1.0.1", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "3D Loader (PLY/PCD)")},
      {"pointcloud-3d-loader", "1.0.1",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Data loader for static 3D files: .pcd and vertex-only .ply load as a point cloud; .ply with faces loads as "
           "a 3D mesh. One snapshot at timestamp 0.")},
      {"protobuf-parser", "1.2.0", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Protobuf Parser")},
      {"protobuf-parser", "1.2.0",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Message parser for Protocol Buffers encoded data. Promotes the well-known Foxglove schemas (PointCloud, "
           "CompressedVideo, CompressedImage, RawImage, ImageAnnotations, SceneUpdate, FrameTransform, PosesInFrame, "
           "CameraCalibration, VoxelGrid, Grid) to builtin scene objects.")},
      {"ros-parser", "1.2.5", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "ROS CDR Parser")},
      {"ros-parser", "1.2.5",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Message parser for ROS1 and ROS2 messages (ros1msg, ros2msg, omgidl). Promotes common sensor and "
           "visualization messages (Image, PointCloud2, OccupancyGrid, GridMap, TF, Markers, and "
           "yolo_msgs/DetectionArray to ImageAnnotations) to builtin scene objects.")},
      {"ros2-topic-subscriber", "1.1.1", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "ROS 2 Topic Subscriber")},
      {"ros2-topic-subscriber", "1.1.1",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Subscribe to ROS 2 topics in real time and stream the decoded fields into PlotJuggler.")},
      {"toolbox-assistant-agent", "0.2.0", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Assistant Agent")},
      {"toolbox-assistant-agent", "0.2.0",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "A chat assistant that drives PlotJuggler through the plugin SDK: lists and describes topics, reads series "
           "statistics, and creates derived timeseries, markers and plot tabs it owns. Uses the Claude Code or Codex "
           "CLI already installed and signed in on your machine; the plugin stores no API keys. Linux, macOS and "
           "Windows.")},
      {"toolbox-mosaico", "1.3.0", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Mosaico Cloud Server")},
      {"toolbox-mosaico", "1.3.0",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Browse and import data from Mosaico cloud servers via Apache Arrow Flight. Scalar topics are handed to the "
           "host as arrow-ipc messages and decoded by the parser_arrow plugin (install it alongside). Includes Lua "
           "metadata predicate filter, multi-topic streaming, and time-range selection.")},
      {"toolbox-quaternion", "1.0.1", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Quaternion to RPY")},
      {"toolbox-quaternion", "1.0.1",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Converts quaternion (x, y, z, w) time series into Roll, Pitch, Yaw angles with optional unwrapping and "
           "degree/radian output.")},
      {"toolbox-transform-editor", "1.0.4", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "Transform Editor")},
      {"toolbox-transform-editor", "1.0.4",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Create named derived time series using Lua functions. Equivalent to the Custom Series editor in PJ3.")},
      {"ulog-loader", "1.1.2", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "ULog Loader")},
      {"ulog-loader", "1.1.2",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata", "Data loader for PX4 ULog files. Flight log format for PX4 autopilot.")},
      {"webrtc-client", "1.0.1", QT_TRANSLATE_NOOP("PJ::BundledPluginMetadata", "WebRTC Video Client")},
      {"webrtc-client", "1.0.1",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "Receives live H.264 video via standard WHEP (mediamtx, go2rtc, LiveKit, Cloudflare Stream...) and feeds "
           "each stream to PlotJuggler as canonical PJ.VideoFrame messages. One HTTP request per stream, per-camera "
           "reconnect, mediamtx Control API discovery. H.264 pass-through; no transcode.")},
      {"ardupilot-dataflash", "1.2.0-pj4.rc.1",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginMetadata",
           "ArduPilot DataFlash BIN logs: numeric fields, sensor instances, units, parameters and message timelines.")},
  };
  for (const auto& entry : entries) {
    if (id == QLatin1String(entry.id) && version == QLatin1String(entry.version) &&
        source == QString::fromUtf8(entry.source)) {
      return QCoreApplication::translate("PJ::BundledPluginMetadata", entry.source);
    }
  }
  return source;
}
inline QString bundledPluginError(const QString& id, const QString& version, const QString& source) {
  struct Entry {
    const char* id;
    const char* version;
    const char* source;
  };
  static constexpr Entry entries[] = {
      {"ardupilot-dataflash", "1.2.0-pj4.rc.1",
       QT_TRANSLATE_NOOP("PJ::BundledPluginDiagnostics", "ArduPilot BIN requires a string filepath")},
      {"ardupilot-dataflash", "1.2.0-pj4.rc.1",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginDiagnostics", "ArduPilot BIN requires a nonempty filepath without NUL bytes")},
      {"ardupilot-dataflash", "1.2.0-pj4.rc.1",
       QT_TRANSLATE_NOOP("PJ::BundledPluginDiagnostics", "ArduPilot BIN: no filepath configured")},
      {"ardupilot-dataflash", "1.2.0-pj4.rc.1",
       QT_TRANSLATE_NOOP("PJ::BundledPluginDiagnostics", "ArduPilot BIN: cannot open file")},
      {"ardupilot-dataflash", "1.2.0-pj4.rc.1",
       QT_TRANSLATE_NOOP("PJ::BundledPluginDiagnostics", "ArduPilot BIN: unsupported file size")},
      {"ardupilot-dataflash", "1.2.0-pj4.rc.1",
       QT_TRANSLATE_NOOP(
           "PJ::BundledPluginDiagnostics", "ArduPilot BIN: file read failed or file changed during import")},
      {"ardupilot-dataflash", "1.2.0-pj4.rc.1",
       QT_TRANSLATE_NOOP("PJ::BundledPluginDiagnostics", "ArduPilot BIN: timestamp exceeds the SDK nanosecond range")},
      {"csv-loader", "1.0.7", QT_TRANSLATE_NOOP("PJ::BundledPluginDiagnostics", "invalid config JSON")},
      {"csv-loader", "1.0.7", QT_TRANSLATE_NOOP("PJ::BundledPluginDiagnostics", "invalid config")},
      {"csv-loader", "1.0.7", QT_TRANSLATE_NOOP("PJ::BundledPluginDiagnostics", "no filepath configured")},
      {"csv-loader", "1.0.7", QT_TRANSLATE_NOOP("PJ::BundledPluginDiagnostics", "CSV parsing failed")},
      {"csv-loader", "1.0.7", QT_TRANSLATE_NOOP("PJ::BundledPluginDiagnostics", "Loading aborted by user")},
  };
  for (const auto& entry : entries) {
    if (id == QLatin1String(entry.id) && version == QLatin1String(entry.version) &&
        source == QString::fromUtf8(entry.source)) {
      return QCoreApplication::translate("PJ::BundledPluginDiagnostics", entry.source);
    }
  }
  return source;
}
}  // namespace PJ
