import pyrealsense2.pyrealsense2 as rs
import numpy as np
import cv2
import serial
import time

ser = serial.Serial('/dev/ttyACM0', 9600)

# Realsenseカメラの設定
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# カメラの開始
pipeline.start(config)

num = 0

try:
    while True:
        # フレームの取得
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:0
        continue

        # フレームをnumpy配列に変換
        color_image = np.asanyarray(color_frame.get_data())

        # 赤い領域を閾値処理で検出
        lower_red = np.array([0, 0, 100]) #bgr
        upper_red = np.array([60, 60, 170])
        mask_red = cv2.inRange(color_image, lower_red, upper_red)

        # 青い領域を閾値処理で検出
        lower_blue = np.array([100, 0, 0]) 
        upper_blue = np.array([170, 60, 60])
        mask_blue = cv2.inRange(color_image, lower_blue, upper_blue)

        # 黄色領域を閾値処理で検出
        lower_yelow = np.array([50, 100, 90]) 
        upper_yelow = np.array([80, 160, 150])
        mask_yelow = cv2.inRange(color_image, lower_yelow, upper_yelow)

        # 輪郭を見つける        
        contours_red, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours_blue, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours_yellow, _ = cv2.findContours(mask_yelow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 輪郭が見つかった場合
        if contours_red:
            # 最大の輪郭を見つける
            max_contour_r = max(contours_red, key=cv2.contourArea)
            # 輪郭の中心を計算
            M = cv2.moments(max_contour_r)
            if M["m00"] != 0:
                cXr = int(M["m10"] / M["m00"])
                cYr = int(M["m01"] / M["m00"])
                # 中心に赤い点を描画
                cv2.circle(color_image, (cXr, cYr), 5, (0, 0, 255), -1)
                if cXr<=340 and cXr>=300 and cYr<=260 and cYr>=220:
                    if num!=1:
                        num = 1
                        print(b"w")
                        ser.write(b'w')
                if cXr > 340 :
                    print(b'r')
                    ser.write(b'r')
                    time.sleep(0.5)
                if cXr < 300:#nen
                    print(b'l')
                    ser.write(b'l')
                    time.sleep(0.5)

        # 輪郭が見つかった場合
        if contours_blue:
            # 最大の輪郭を見つける
            max_contour_b = max(contours_blue, key=cv2.contourArea)
            # 輪郭の中心を計算
            M = cv2.moments(max_contour_b)
            if M["m00"] != 0:
                cXb = int(M["m10"] / M["m00"])
                cYb = int(M["m01"] / M["m00"])
                # 中心に赤い点を描画
                cv2.circle(color_image, (cXb, cYb), 5, (255, 0, 0), -1)
                if cXb<=340 and cXb>=300 and cYb<=260 and cYb>=220:
                    if num!=2:
                        num=2
                        print(b"a")
                        ser.write(b'a')

        # 輪郭が見つかった場合
        if contours_yellow:
            # 最大の輪郭を見つける
            max_contour_y = max(contours_yellow, key=cv2.contourArea)
            # 輪郭の中心を計算
            M = cv2.moments(max_contour_y)
            if M["m00"] != 0:
                cXy = int(M["m10"] / M["m00"])
                cYy = int(M["m01"] / M["m00"])
                # 中心に赤い点を描画
                cv2.circle(color_image, (cXy, cYy), 5, (0, 255, 255), -1)
                if cXy<=340 and cXy>=300 and cYy<=260 and cYy>=220:
                    if num!=3:
                        num = 3
                        print(b"d")
                        ser.write(b'd')
        

        # 結果を表示
        # 画面の中心座標
        center_x = color_image.shape[1] // 2
        center_y = color_image.shape[0] // 2

        # 十字線を描画
        cv2.line(color_image, (center_x, 0), (center_x, color_image.shape[0]), (255, 255, 255), 1)
        cv2.line(color_image, (0, center_y), (color_image.shape[1], center_y), (255, 255, 255), 1)

        cv2.imshow("Realsense", color_image)
        time.sleep(0.1)


        # 終了条件
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # カメラの停止
    pipeline.stop()
    cv2.destroyAllWindows()
