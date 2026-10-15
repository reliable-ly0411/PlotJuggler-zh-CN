add_subdirectory(DataLoadCSV)
add_subdirectory(DataLoadMCAP)
add_subdirectory(DataLoadParquet)
add_subdirectory(DataLoadULog)

add_subdirectory(DataStreamSample)
add_subdirectory(DataStreamWebsocket)
add_subdirectory(DataStreamUDP)
add_subdirectory(DataStreamMQTT)
add_subdirectory(DataStreamZMQ)
add_subdirectory(DataStreamFoxgloveBridge)
add_subdirectory(DataStreamPlotJugglerBridge)
add_subdirectory(DataStreamSerialPort)

add_subdirectory(VideoViewer)

add_subdirectory(ToolboxQuaternion)
add_subdirectory(ToolboxFFT)
add_subdirectory(ToolboxLuaEditor)
add_subdirectory(ToolboxCSV)
add_subdirectory(ToolboxMosaico)

add_subdirectory(ParserProtobuf)
add_subdirectory(ParserROS)
add_subdirectory(ParserDataTamer)
add_subdirectory(ParserLineInflux)

add_subdirectory(PluginsZcm)

# The loader is discovered with the other bundled shared plugins.
option(PJ_BUILD_ARDUPILOT "Build and bundle the ArduPilot DataFlash BIN loader" ON)
if(PJ_BUILD_ARDUPILOT)
  add_subdirectory(DataLoadAPBin)
endif()
