import pyrealsense2 as rs
import cv2
import numpy as np
import serial
import time

# シリアル接続設定
ser = serial.Serial('/dev/ttyACM0', 9600)
time.sleep(2)

def main():
    # RealSenseパイプラインを設定
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480)  # カラーストリームのみを有効化

    # パイプラインを開始
    pipeline.start(config)

    try:
        while True:
            # 新しいフレームセットを取得
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            color_img = np.asanyarray(color_frame.get_data())
            color_img = cv2.cvtColor(color_img, cv2.COLOR_RGB2BGR)

            # カラー画像をHSVに変換
            hsv_img = cv2.cvtColor(color_img, cv2.COLOR_BGR2HSV)

            # 赤色と青色のマスクを作成
            lower_red = np.array([140, 180, 110])  # 色相、彩度、明度
            upper_red = np.array([180, 220, 150])
            lower_blue = np.array([90, 190, 70])
            upper_blue = np.array([130, 230, 110])

            red_mask = cv2.inRange(hsv_img, lower_red, upper_red)
            blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

            # 輪郭を検出
            red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            blue_contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 最大の赤色と青色の輪郭を見つける
            max_red_contour = max(red_contours, key=cv2.contourArea) if red_contours else None
            max_blue_contour = max(blue_contours, key=cv2.contourArea) if blue_contours else None

            # 出力画像の作成
            output_img = color_img.copy()
            height, width = output_img.shape[:2]
            center_x, center_y = width // 2, height // 2

            # 画面中央に白い十字線を描画
            cv2.line(output_img, (center_x, 0), (center_x, height), (255, 255, 255), 2)  # 縦線
            cv2.line(output_img, (0, center_y), (width, center_y), (255, 255, 255), 2)  # 横線

            # 赤い領域の中心を取得して、右・左でシリアルデータ送信
            if max_red_contour is not None:
                x, y, w, h = cv2.boundingRect(max_red_contour)
                red_center_x = x + w // 2
                red_center_y = y + h // 2
                cv2.circle(output_img, (red_center_x, red_center_y), 5, (0, 0, 255), -1)

            # 青い領域の中心を取得して、右・左でシリアルデータ送信
            if max_blue_contour is not None:
                x, y, w, h = cv2.boundingRect(max_blue_contour)
                blue_center_x = x + w // 2
                blue_center_y = y + h // 2
                cv2.circle(output_img, (blue_center_x, blue_center_y), 5, (255, 0, 0), -1)

                if center_x - 80 <= blue_center_x and blue_center_x <= center_x +80:
                    print("Sending 'w' via serial)")
                    ser.write(b'w')
                # 画面中心から160ピクセル以上右の場合に'r'を送信                       
                elif blue_center_x > center_x + 80:
                    print("Sending 'r' via serial (right for blue)")
                    ser.write(b'r')
                # 画面中心から160ピクセル以上左の場合に'l'を送信
                elif blue_center_x < center_x - 80:
                    print("Sending 'l' via serial (left for blue)")
                    ser.write(b'l')

            # 出力画像を表示
            cv2.imshow('Color Marking', output_img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        # パイプラインを停止
        pipeline.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
