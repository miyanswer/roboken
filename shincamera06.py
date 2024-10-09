import pyrealsense2.pyrealsense2 as rs
import numpy as np
import cv2
import serial
import time

# シリアル通信の設定
ser = serial.Serial('/dev/ttyACM0', 9600)

# Realsenseカメラの設定
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

# カメラの開始
pipeline.start(config)

num = 0

def find_contour_center(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        max_contour = max(contours, key=cv2.contourArea)
        M = cv2.moments(max_contour)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            return cX, cY
    return None, None

try:
    while True:
        # フレームの取得
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        if not color_frame or not depth_frame:
            continue

        # フレームをnumpy配列に変換
        color_image = np.asanyarray(color_frame.get_data())
        depth_image = np.asanyarray(depth_frame.get_data())

        # 赤い領域を閾値処理で検出
        lower_red = np.array([0, 0, 100])  # BGR
        upper_red = np.array([60, 60, 170])
        mask_red = cv2.inRange(color_image, lower_red, upper_red)

        # 青い領域を閾値処理で検出
        lower_blue = np.array([100, 0, 0])  # BGR
        upper_blue = np.array([170, 60, 60])
        mask_blue = cv2.inRange(color_image, lower_blue, upper_blue)

        # 黄色い領域を閾値処理で検出
        lower_yellow = np.array([0, 100, 100])  # BGR
        upper_yellow = np.array([60, 255, 255])
        mask_yellow = cv2.inRange(color_image, lower_yellow, upper_yellow)

        # 各色の輪郭の中心を見つける
        cXr, cYr = find_contour_center(mask_red)
        cXb, cYb = find_contour_center(mask_blue)
        cXy, cYy = find_contour_center(mask_yellow)

        # 赤色の追跡
        if cXr is not None and cYr is not None:
            # 中心に赤い点を描画
            cv2.circle(color_image, (cXr, cYr), 5, (0, 0, 255), -1)
            depth = depth_frame.get_distance(cXr, cYr)

            # 画面の中心座標
            center_x = color_image.shape[1] // 2
            center_y = color_image.shape[0] // 2

            # 物体が画面中央に来るように追跡する
            if depth > 0 and depth < 1.0:  # 1.0メートル以内
                if num != 1:
                    num = 1
                    print(b"w")
                    ser.write(b'w')
            elif depth >= 1.0 and depth < 2.0:  # 1.0メートル以上2.0メートル未満
                if cXr > center_x + 20:  # 画面の右側にある場合
                    print(b'r')  # 右に回転
                    ser.write(b'r')
                    time.sleep(0.5)
                elif cXr < center_x - 20:  # 画面の左側にある場合
                    print(b'l')  # 左に回転
                    ser.write(b'l')
                    time.sleep(0.5)

        # 青色の追跡
        if cXb is not None and cYb is not None:
            # 中心に青い点を描画
            cv2.circle(color_image, (cXb, cYb), 5, (255, 0, 0), -1)

        # 黄色の追跡
        if cXy is not None and cYy is not None:
            # 中心に黄色い点を描画
            cv2.circle(color_image, (cXy, cYy), 5, (0, 255, 255), -1)

        # 十字線を描画
        cv2.line(color_image, (center_x, 0), (center_x, color_image.shape[0]), (255, 255, 255), 1)
        cv2.line(color_image, (0, center_y), (color_image.shape[1], center_y), (255, 255, 255), 1)

        # 結果を表示
        cv2.imshow("Realsense", color_image)
        time.sleep(0.1)

        # 終了条件
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # カメラの停止
    pipeline.stop()
    cv2.destroyAllWindows()
