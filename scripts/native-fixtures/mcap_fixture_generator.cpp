// SPDX-License-Identifier: MPL-2.0
#define MCAP_IMPLEMENTATION
#define MCAP_COMPRESSION_NO_LZ4
#define MCAP_COMPRESSION_NO_ZSTD
#include <mcap/reader.hpp>
#include <mcap/writer.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

/// Generate synthetic channels, then independently reopen and validate every message.
void generateAndVerify(const std::string& path, const std::string& image, bool dual) {
  const unsigned count = dual ? 8400 : 90;
  const std::vector<std::string> topics = dual
      ? std::vector<std::string>{"/camera/color/image", "/camera/depth/image", "/imu/accel/sample", "/imu/gyro/sample"}
      : std::vector<std::string>{"/camera/color/image"};
  const std::string scalar = R"({"x":0.1,"y":0.2,"z":0.3})";
  mcap::McapWriter writer;
  mcap::McapWriterOptions options("json");
  options.compression = mcap::Compression::None;
  auto check = [](const mcap::Status& s) { if (!s.ok()) throw std::runtime_error(s.message); };
  check(writer.open(path, options));
  mcap::Schema image_schema("foxglove.CompressedImage", "jsonschema", R"({"type":"object","properties":{"timestamp":{"type":"object"},"frame_id":{"type":"string"},"format":{"type":"string"},"data":{"type":"string","contentEncoding":"base64"}}})");
  mcap::Schema scalar_schema("synthetic.ImuSample", "jsonschema", R"({"type":"object","properties":{"x":{"type":"number"},"y":{"type":"number"},"z":{"type":"number"}}})");
  writer.addSchema(image_schema);
  writer.addSchema(scalar_schema);
  std::vector<mcap::Channel> channels;
  for (size_t i = 0; i < topics.size(); ++i) {
    channels.emplace_back(topics[i], "json", i < 2 ? image_schema.id : scalar_schema.id);
    writer.addChannel(channels.back());
  }
  for (unsigned i = 0; i < count; ++i) {
    for (size_t c = 0; c < channels.size(); ++c) {
      const auto& payload = c < 2 ? image : scalar;
      mcap::Message m;
      m.channelId = channels[c].id;
      m.sequence = i;
      m.logTime = 1000000000ULL + i * 33333333ULL;
      m.publishTime = m.logTime;
      m.data = reinterpret_cast<const std::byte*>(payload.data());
      m.dataSize = payload.size();
      check(writer.write(m));
    }
  }
  writer.close();
  mcap::McapReader reader;
  check(reader.open(path));
  check(reader.readSummary(mcap::ReadSummaryMethod::NoFallbackScan));
  if (reader.channels().size() != topics.size()) throw std::runtime_error("channel count mismatch");
  std::vector<unsigned> seen(topics.size());
  for (const auto& view : reader.readMessages(check)) {
    size_t c = 0;
    while (c < topics.size() && topics[c] != view.channel->topic) ++c;
    if (c == topics.size()) throw std::runtime_error("unknown topic");
    const auto& m = view.message;
    const auto& payload = c < 2 ? image : scalar;
    if (view.channel->messageEncoding != "json" || !view.schema ||
        view.schema->name != (c < 2 ? "foxglove.CompressedImage" : "synthetic.ImuSample") ||
        view.schema->encoding != "jsonschema" || m.sequence != seen[c] ||
        m.logTime != 1000000000ULL + seen[c] * 33333333ULL || m.publishTime != m.logTime ||
        std::string(reinterpret_cast<const char*>(m.data), m.dataSize) != payload) {
      throw std::runtime_error("message semantic readback mismatch");
    }
    ++seen[c];
  }
  for (auto n : seen) if (n != count) throw std::runtime_error("message count mismatch");
  std::cout << "{\"channels\":" << topics.size() << ",\"messages_per_channel\":" << count
            << ",\"all_payloads_timestamps_sequences_validated\":true}\n";
}

/// Paths are supplied by the task-owned orchestrator; no ambient files or network are read.
int main(int argc, char** argv) {
  try {
    if (argc != 3) throw std::runtime_error("usage: generator image.json output-directory");
    const std::filesystem::path out(argv[2]);
    if (!std::filesystem::is_directory(out) ||
        std::filesystem::exists(out / "test_images.mcap") ||
        std::filesystem::exists(out / "potato.mcap")) {
      throw std::runtime_error("output directory must exist with no existing MCAP fixtures");
    }
    std::ifstream input(argv[1]);
    if (!input) throw std::runtime_error("cannot read image JSON");
    const std::string image((std::istreambuf_iterator<char>(input)), {});
    generateAndVerify(std::string(argv[2]) + "/test_images.mcap", image, false);
    generateAndVerify(std::string(argv[2]) + "/potato.mcap", image, true);
    return 0;
  } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
