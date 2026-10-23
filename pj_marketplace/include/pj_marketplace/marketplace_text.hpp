// SPDX-License-Identifier: MPL-2.0
#pragma once
#include <pj_widgets/BundledPluginText.h>

#include <QCoreApplication>
#include <QString>

namespace PJ {
// Presentation-only metadata, independent of installation state and plugin version.
// Exact ID/source matching prevents stale translations from hiding upstream changes.
inline QString marketplacePluginText(const QString& id, const QString& version, const QString& source) {
  struct Entry {
    const char* id;
    const char* source;
  };
  static constexpr Entry entries[] = {
      {"arrow-parser", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Arrow IPC Parser")},
      {"arrow-parser",
       QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Message parser for self-describing Arrow IPC streams.")},
      {"blf-loader", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "BLF Loader")},
      {"blf-loader", QT_TRANSLATE_NOOP(
                         "PJ::MarketplaceCatalog",
                         "Data loader for Vector BLF (Binary Logging Format) CAN logs, decoded to signals via DBC.")},
      {"csv-loader", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "CSV Loader")},
      {"csv-loader", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Data loader for CSV files.")},
      {"data-tamer-parser", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "DataTamer Parser")},
      {"data-tamer-parser", QT_TRANSLATE_NOOP(
                                "PJ::MarketplaceCatalog",
                                "Message parser for DataTamer encoded data. Efficient serialization for robotics.")},
      {"dummy-streamer", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Dummy Streamer")},
      {"dummy-streamer",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Generates synthetic sine, cosine, sawtooth, and noise signals for testing and demonstration.")},
      {"foxglove-bridge", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Foxglove Bridge")},
      {"foxglove-bridge",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Connect to Foxglove WebSocket server for ROS data streaming. Compatible with Foxglove Studio.")},
      {"json-parser", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "JSON Parser")},
      {"json-parser",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog", "Message parser for JSON, CBOR, MessagePack, and BSON encoded data.")},
      {"lerobot-loader", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "LeRobot Loader")},
      {"lerobot-loader",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Data loader for LeRobot v2.x and v3.0 datasets: flattened numeric series + per-camera video on a shared "
           "timeline. v3.0 datasets use a consolidated per-shard Parquet/MP4 layout with relational metadata; the "
           "plugin reads meta/episodes/*.parquet to resolve each episode's row range and clip window.")},
      {"lsl-streaming", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Lab Streaming Layer")},
      {"lsl-streaming", QT_TRANSLATE_NOOP(
                            "PJ::MarketplaceCatalog",
                            "Real-time streaming from Lab Streaming Layer (LSL) sources, including numeric and marker "
                            "(string) streams.")},
      {"mcap-loader", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "MCAP Loader")},
      {"mcap-loader", QT_TRANSLATE_NOOP(
                          "PJ::MarketplaceCatalog",
                          "Data loader for MCAP files and split ROS 2 bags (metadata.yaml). Supports ROS1, ROS2, "
                          "Protobuf, and JSON message encodings.")},
      {"mf4-loader", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "MF4/MDF Loader")},
      {"mf4-loader", QT_TRANSLATE_NOOP(
                         "PJ::MarketplaceCatalog",
                         "Data loader for ASAM MDF / MF4 measurement files (automotive, CAN/LIN bus logging).")},
      {"mp4-loader", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "MP4 Loader")},
      {"mp4-loader",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Data loader for .mp4 video files. Reads the container's creation_time tag (when present) so the host can "
           "anchor the video on a wall-clock timeline; supports multi-file selection via the standard File dialog.")},
      {"mqtt-subscriber", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "MQTT Subscriber")},
      {"mqtt-subscriber",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Real-time data streaming via MQTT protocol. Subscribe to topics and visualize live data.")},
      {"parquet-loader", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Parquet Loader")},
      {"parquet-loader",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog", "Data loader for Apache Parquet files. Efficient columnar storage format.")},
      {"plotjuggler-bridge", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "PlotJuggler Bridge")},
      {"plotjuggler-bridge", QT_TRANSLATE_NOOP(
                                 "PJ::MarketplaceCatalog",
                                 "Connect to PlotJuggler Bridge server for generic data streaming over WebSocket.")},
      {"pointcloud-3d-loader", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "3D Loader (PLY/PCD)")},
      {"pointcloud-3d-loader", QT_TRANSLATE_NOOP(
                                   "PJ::MarketplaceCatalog",
                                   "Data loader for static 3D files: .pcd and vertex-only .ply load as a point cloud; "
                                   ".ply with faces loads as a 3D mesh. One snapshot at timestamp 0.")},
      {"protobuf-parser", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Protobuf Parser")},
      {"protobuf-parser",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Message parser for Protocol Buffers encoded data. Promotes the well-known Foxglove schemas (PointCloud, "
           "CompressedVideo, CompressedImage, RawImage, ImageAnnotations, SceneUpdate, FrameTransform, PosesInFrame, "
           "CameraCalibration, VoxelGrid, Grid) to builtin scene objects.")},
      {"ros-parser", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "ROS CDR Parser")},
      {"ros-parser", QT_TRANSLATE_NOOP(
                         "PJ::MarketplaceCatalog",
                         "Message parser for ROS1 and ROS2 messages (ros1msg, ros2msg, omgidl). Promotes common sensor "
                         "and visualization messages (Image, PointCloud2, OccupancyGrid, GridMap, TF, Markers, and "
                         "yolo_msgs/DetectionArray to ImageAnnotations) to builtin scene objects.")},
      {"ros2-topic-subscriber", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "ROS 2 Topic Subscriber")},
      {"ros2-topic-subscriber",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Subscribe to ROS 2 topics in real time and stream the decoded fields into PlotJuggler.")},
      {"toolbox-anomaly-detector", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Anomaly Detector")},
      {"toolbox-anomaly-detector",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Write Lua anomaly rules over time series and emit plot markers (regions / events) when a rule fires.")},
      {"toolbox-assistant-agent", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Assistant Agent")},
      {"toolbox-assistant-agent",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "A chat assistant that drives PlotJuggler through the plugin SDK: lists and describes topics, reads series "
           "statistics, and creates derived timeseries, markers and plot tabs it owns. Uses the Claude Code or Codex "
           "CLI already installed and signed in on your machine; the plugin stores no API keys. Linux, macOS and "
           "Windows.")},
      {"toolbox-data-exporter", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "CSV/Parquet Exporter")},
      {"toolbox-data-exporter",
       QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Export selected time series to CSV or Parquet files.")},
      {"toolbox-fft", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Fast Fourier Transform")},
      {"toolbox-fft",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog", "Compute the frequency-domain amplitude of numeric time series using FFT.")},
      {"toolbox-mosaico", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Mosaico Cloud Server")},
      {"toolbox-mosaico",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Browse and import data from Mosaico cloud servers via Apache Arrow Flight. Scalar topics are handed to the "
           "host as arrow-ipc messages and decoded by the parser_arrow plugin (install it alongside). Includes Lua "
           "metadata predicate filter, multi-topic streaming, and time-range selection.")},
      {"toolbox-quaternion", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Quaternion to RPY")},
      {"toolbox-quaternion", QT_TRANSLATE_NOOP(
                                 "PJ::MarketplaceCatalog",
                                 "Converts quaternion (x, y, z, w) time series into Roll, Pitch, Yaw angles with "
                                 "optional unwrapping and degree/radian output.")},
      {"toolbox-transform-editor", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "Transform Editor")},
      {"toolbox-transform-editor",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Create named derived time series using Lua functions. Equivalent to the Custom Series editor in PJ3.")},
      {"udp-server", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "UDP Server")},
      {"udp-server",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog", "Real-time data streaming via UDP. Supports unicast and multicast IPv4/IPv6.")},
      {"ulog-loader", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "ULog Loader")},
      {"ulog-loader",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog", "Data loader for PX4 ULog files. Flight log format for PX4 autopilot.")},
      {"webrtc-client", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "WebRTC Video Client")},
      {"webrtc-client",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Receives live H.264 video via standard WHEP (mediamtx, go2rtc, LiveKit, Cloudflare Stream...) and feeds "
           "each stream to PlotJuggler as canonical PJ.VideoFrame messages. One HTTP request per stream, per-camera "
           "reconnect, mediamtx Control API discovery. H.264 pass-through; no transcode.")},
      {"zmq-subscriber", QT_TRANSLATE_NOOP("PJ::MarketplaceCatalog", "ZMQ Subscriber")},
      {"zmq-subscriber",
       QT_TRANSLATE_NOOP(
           "PJ::MarketplaceCatalog",
           "Real-time data streaming via ZeroMQ. High-performance messaging for distributed systems.")},
  };
  for (const auto& entry : entries) {
    if (id == QLatin1String(entry.id) && source == QString::fromUtf8(entry.source)) {
      return QCoreApplication::translate("PJ::MarketplaceCatalog", entry.source);
    }
  }
  return bundledPluginText(id, version, source);
}
}  // namespace PJ
