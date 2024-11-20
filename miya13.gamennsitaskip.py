import pyrealsense2 as rs
import cv2
import numpy as np
import serial
import time
import simpleaudio as sa

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

    #シリアル連続阻止
    previous_command = None

    # 再生する WAV ファイルのパス
    wave_obj_men = sa.WaveObject.from_wave_file("men.wav")
    wave_obj_dou = sa.WaveObject.from_wave_file("dou.wav")
    wave_obj_kote = sa.WaveObject.from_wave_file("kote.wav")

    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').rstrip()
                print(line)
                if line == "m" :
                    play_obj = wave_obj_men.play()
                    time.sleep(1)#再生時間
                    play_obj.stop()#再生停止
                    #play_obj.wait_done()#音声再生のときにプログラム停止コード  
                elif line == "d":
                    play_obj = wave_obj_dou.play()
                    time.sleep(1)
                    play_obj.stop()
                    #play_obj.wait_done()
                elif line == "k":
                    play_obj = wave_obj_kote.play()
                    time.sleep(1)
                    play_obj.stop()
                    #play_obj.wait_done()

            # 新しいフレームセットを取得
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            color_img = np.asanyarray(color_frame.get_data())
            color_img = cv2.cvtColor(color_img, cv2.COLOR_RGB2BGR)

            # カラー画像をHSVに変換
            hsv_img = cv2.cvtColor(color_img, cv2.COLOR_BGR2HSV)

            # 赤色と青色のマスクを作成
            lower_red = np.array([1, 160, 185])  # 色相、彩度、明度
            upper_red = np.array([15, 230, 255]) #2,195,220
            lower_blue = np.array([100, 185, 65])
            upper_blue = np.array([120, 255, 116]) #107,225,100-105

            red_mask = cv2.inRange(hsv_img, lower_red, upper_red)
            blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

            # 輪郭を検出
            red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            blue_contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 出力画像の作成
            output_img = color_img.copy()
            height, width = output_img.shape[:2]
            center_x, center_y = width // 2, height // 2

            # 画面中央に白い十字線を描画(始点、終点)
            cv2.line(output_img, (center_x, 180), (center_x, 300), (255, 255, 255), 2)  # 縦線
            cv2.line(output_img, (0, center_y), (width, center_y), (255, 255, 255), 2)  # 横線
            #左右160ピクセル縦線
            cv2.line(output_img, (center_x - 160, 0), (center_x - 160, height), (255, 255, 255), 2)
            cv2.line(output_img, (center_x + 160, 0), (center_x + 160, height), (255, 255, 255), 2)
            #中央から90ピクセル下の横線
            cv2.line(output_img, (0, center_y + 90), (width, center_y + 90), (255, 255, 255), 2)

            # 赤い領域の輪郭を黄色で囲む（面積が350平方ピクセル以上の場合のみ）
            for contour in red_contours:
                if cv2.contourArea(contour) > 350:
                    cv2.drawContours(output_img, [contour], -1, (0, 255, 255), 2)
                    # 重心を取得
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        red_center_x = int(M["m10"] / M["m00"])
                        red_center_y = int(M["m01"] / M["m00"])
                        cv2.circle(output_img, (red_center_x, red_center_y), 5, (0, 0, 255), -1)

            # 青い領域の輪郭を黄色で囲む（面積が800平方ピクセル以上の場合のみ）
            for contour in blue_contours:
                if 800 < cv2.contourArea(contour) < 4800:
                    # 重心を取得
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        blue_center_x = int(M["m10"] / M["m00"])
                        blue_center_y = int(M["m01"] / M["m00"])
       
                        #画面中央から90ピクセル下以上の青は無視
                        if blue_center_y > center_y +90:
                            continue

                        cv2.drawContours(output_img, [contour], -1, (0, 255, 255), 2)
                        cv2.circle(output_img, (blue_center_x, blue_center_y), 5, (255, 0, 0), -1)

                    # 同じシリアルが送信されないようにする
                    # 中心から左右120ピクセル以内のとき'w'を送信
                    if center_x - 160 <= blue_center_x <= center_x + 160:
                        current_command = 'w'
                    # 画面中心から120ピクセル以上右の場合に'r'を送信  
                    elif blue_center_x > center_x + 160:
                        current_command = 'r'
                    # 画面中心から120ピクセル以上左の場合に'l'を送信
                    elif blue_center_x < center_x -160:
                        current_command = 'l'
                    else:
                        current_command = None

                    if current_command and current_command != previous_command:
                        if current_command == 'w':
                            print("Sending 'w' via serial")
                            ser.write(b'w')                     
                        elif current_command == 'r':
                            print("Sending 'r' via serial")
                            ser.write(b'r')
                        elif current_command == 'l':
                            print("Sending 'l' via serial")
                            ser.write(b'l')
                        # 送信したコマンドを前回のコマンドとして更新
                        previous_command = current_command
                    # インターバル
                    time.sleep(0.1)

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