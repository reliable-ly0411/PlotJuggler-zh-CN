// SPDX-License-Identifier: MPL-2.0
#pragma once
#include <QTcpServer>
#include <QTcpSocket>
using namespace Qt::StringLiterals;
// Local responses keep release-channel tests deterministic and offline.
class Server : public QTcpServer {
 public:
  explicit Server(QByteArray body) {
    connect(this, &QTcpServer::newConnection, this, [this, body]() {
      auto* socket = nextPendingConnection();
      connect(socket, &QTcpSocket::readyRead, socket, [socket, body]() {
        socket->readAll();
        socket->write(
            "HTTP/1.1 200 OK\r\nContent-Length: " + QByteArray::number(body.size()) + "\r\nConnection: close\r\n\r\n" +
            body);
        socket->disconnectFromHost();
      });
      connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
    });
    listen(QHostAddress::LocalHost);
  }
  QUrl url() const {
    return QUrl(u"http://127.0.0.1:%1/releases"_s.arg(serverPort()));
  }
};
