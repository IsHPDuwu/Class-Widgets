from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QObject, pyqtSlot, QUrl
from qframelesswindow import FramelessWindow
from qframelesswindow.webengine import FramelessWebEngineView
import sys
import requests

class Bridge(QObject):
    @pyqtSlot(float, float)
    def receiveCoordinates(self, lat, lon):
        print(f"选中坐标：纬度 {lat:.6f}, 经度 {lon:.6f}")
        # 调用反向地理编码 API 获取城市名称
        city = self.get_city_from_coordinates(lat, lon)
        if city:
            print(f"城市名称：{city}")
        else:
            print("无法获取城市名称")

    def get_city_from_coordinates(self, lat, lon):
        # 使用 Nominatim API 进行反向地理编码
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
        headers = {
            'User-Agent': 'ClassWidgets/1.1.7.2 (contact: IsHPDuwu@outlook.com)'  # Nominatim 要求自定义 User-Agent
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 检查请求是否成功
            data = response.json()
            print(data)
            # 从返回的地址中提取城市名称
            address = data.get('address', {})
            # 优先级：city > town > village > locality
            city = address.get('city') or address.get('town') or address.get('village') or address.get('locality')
            return city
        except requests.RequestException as e:
            print(f"反向地理编码请求失败：{e}")
            return None

class MapWindow(FramelessWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("地图选点")

        # Create a central widget and set layout
        self.central_widget = QWidget()
        layout = QVBoxLayout(self.central_widget)
        self.view = FramelessWebEngineView(self.central_widget)
        layout.addWidget(self.view)

        # Set the layout on the FramelessWindow
        self.setLayout(layout)

        # 设置通信桥
        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        # 加载地图 HTML
        self.view.setHtml(self.generateMapHtml(), QUrl(""))

    def generateMapHtml(self):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <title>地图选点</title>
            <style> html, body, #map { height: 100%; margin: 0; background: transparent; } </style>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map', { renderer: L.canvas() }).setView([34.26, 108.95], 13);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap'
                }).addTo(map);

                // 存储当前标记
                var currentMarker = null;

                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.bridge = channel.objects.bridge;
                });

                map.on('click', function(e) {
                    var lat = e.latlng.lat;
                    var lon = e.latlng.lng;
                    // 移除之前的标记（如果存在）
                    if (currentMarker !== null) {
                        map.removeLayer(currentMarker);
                    }
                    // 添加新标记
                    currentMarker = L.marker([lat, lon]).addTo(map);
                    if (window.bridge) {
                        window.bridge.receiveCoordinates(lat, lon);
                    }
                });
            </script>
        </body>
        </html>
        """

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MapWindow()
    win.show()
    sys.exit(app.exec_())