#realsenseでデプスフレームとノーマルカメラに赤青マーキング
#赤青誤差少なければ黄色で囲む
#黄色のｘ座標によってシリアル送信
import pyrealsense2 as rs
import cv2
import numpy as np
import time

def main():
    # RealSenseパイプラインを設定
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color)  # カラーストリームを有効化
    config.enable_stream(rs.stream.depth)  # 深度ストリームを有効化

    # パイプラインを開始
    pipeline.start(config)

    #認識する最大のデプス決める適宜変更する
    max_depth = 1

    # 深度フィルタとカラーマップを作成
    depth_filter = rs.threshold_filter()
    depth_filter.set_option(rs.option.min_distance, 0.0)
    depth_filter.set_option(rs.option.max_distance, max_depth)
    color_map = rs.colorizer()

    # FPS計測のための変数を初期化
    prev_time = time.time()
    frame_count = 0
    fps = 0

    try:
        while True:
            # 新しいフレームセットを待機し取得
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()

            # 深度データにフィルタとカラーマッピングを適用
            filtered_depth = depth_filter.process(depth_frame)
            colorized_depth = color_map.process(filtered_depth)

            # RealSenseのカラーフレームをOpenCVマトリックスに変換
            color_img = np.asanyarray(color_frame.get_data())
            color_img = cv2.cvtColor(color_img, cv2.COLOR_RGB2BGR)

            # 深度データを単一チャンネルに変換
            depth_img = np.asanyarray(colorized_depth.get_data())
            depth_img_single = cv2.cvtColor(depth_img, cv2.COLOR_BGR2GRAY)

            # 深度データのマスクを作成 (2メートル以上の距離)
            _, depth_mask = cv2.threshold(depth_img_single, max_depth, 255, cv2.THRESH_BINARY)

            # カラー画像を深度画像サイズにリサイズ
            depth_height, depth_width = depth_img.shape[:2]
            color_resized = cv2.resize(color_img, (depth_width, depth_height), interpolation=cv2.INTER_LINEAR)

            # 深度マスクをカラー画像サイズにリサイズ
            depth_mask_resized = cv2.resize(depth_mask, color_resized.shape[1::-1], interpolation=cv2.INTER_NEAREST)

            # 深度マスクをカラー画像に適用
            color_masked = np.zeros_like(color_resized)
            color_masked[depth_mask_resized == 255] = color_resized[depth_mask_resized == 255]

            # カラー画像をHSVに変換
            hsv_img = cv2.cvtColor(color_masked, cv2.COLOR_BGR2HSV)

            # 赤色の範囲を定義
            lower_red1 = np.array([0, 190, 70])
            upper_red1 = np.array([20, 250, 110])
            lower_red2 = np.array([170, 190, 70])
            upper_red2 = np.array([180, 250, 110])

            # 青色の範囲を定義
            lower_blue1 = np.array([100, 200, 50])
            upper_blue1 = np.array([120, 240, 70])
            lower_blue2 = np.array([180, 200, 50])
            upper_blue2 = np.array([190, 240, 70])

            # 赤色範囲ごとにマスクを作成
            mask_red1 = cv2.inRange(hsv_img, lower_red1, upper_red1)
            mask_red2 = cv2.inRange(hsv_img, lower_red2, upper_red2)
            red_mask = cv2.bitwise_or(mask_red1, mask_red2)

            # 青色範囲ごとにマスクを作成
            mask_blue1 = cv2.inRange(hsv_img, lower_blue1, upper_blue1)
            mask_blue2 = cv2.inRange(hsv_img, lower_blue2, upper_blue2)
            blue_mask = cv2.bitwise_or(mask_blue1, mask_blue2)

            # 赤色マスクで輪郭を検出
            red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 青色マスクで輪郭を検出
            blue_contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 最大の赤色領域を探す
            max_area_red = 0
            largest_contour_red = None
            for contour_red in red_contours:
                area_red = cv2.contourArea(contour_red)
                if area_red > max_area_red:
                    max_area_red = area_red
                    largest_contour_red = contour_red

            # 最大の青色領域を探す
            max_area_blue = 0
            largest_contour_blue = None
            for contour_blue in blue_contours:
                area_blue = cv2.contourArea(contour_blue)
                if area_blue > max_area_blue:
                    max_area_blue = area_blue
                    largest_contour_blue = contour_blue

            # 結果画像を初期化
            output_img = color_resized.copy()
            center_offset = (depth_width // 2, depth_height // 2)

            # 最大の赤色領域とそのバウンディングボックスを描画
            if largest_contour_red is not None:
                bounding_rect_red = cv2.boundingRect(largest_contour_red)
                cv2.rectangle(output_img, bounding_rect_red, (0, 0, 255), 2)  # 緑の矩形を描画

                # バウンディングボックスの中心を計算
                center_red = (bounding_rect_red[0] + bounding_rect_red[2] // 2,
                             bounding_rect_red[1] + bounding_rect_red[3] // 2)

                # (0, 0) を中心にし、Y軸を逆にした座標系に変換
                center_in_screen_red = (center_red[0] - center_offset[0], center_offset[1] - center_red[1])

                # 赤色領域の中心の深度値を確認
                if 0 <= center_red[0] < depth_width and 0 <= center_red[1] < depth_height:
                    depth_value_red = depth_frame.get_distance(center_red[0], center_red[1])  # 赤色領域の中心の深度値を取得

                    if depth_value_red < max_depth:  # 深度値が2メートル未満
                        # 赤色領域の中心の座標を新しい座標系で出力
                        print(f"Red Center: ({center_in_screen_red[0]}, {center_in_screen_red[1]}, {depth_value_red})")

                        # 中心に赤い点を描画
                        cv2.circle(output_img, center_red, 5, (0, 0, 255), -1)  # 赤い点を描画

            # 最大の青色領域とそのバウンディングボックスを描画
            if largest_contour_blue is not None:
                bounding_rect_blue = cv2.boundingRect(largest_contour_blue)
                cv2.rectangle(output_img, bounding_rect_blue, (255, 0, 0), 2)  # 青の矩形を描画

                # バウンディングボックスの中心を計算
                center_blue = (bounding_rect_blue[0] + bounding_rect_blue[2] // 2,
                              bounding_rect_blue[1] + bounding_rect_blue[3] // 2)

                # (0, 0) を中心にし、Y軸を逆にした座標系に変換
                center_in_screen_blue = (center_blue[0] - center_offset[0], center_offset[1] - center_blue[1])

                # 青色領域の中心の深度値を確認
                if 0 <= center_blue[0] < depth_width and 0 <= center_blue[1] < depth_height:
                    depth_value_blue = depth_frame.get_distance(center_blue[0], center_blue[1])  # 青色領域の中心の深度値を取得

                    if depth_value_blue < max_depth:  # 深度値が2メートル未満
                        # 青色領域の中心の座標を新しい座標系で出力
                        print(f"Blue Center: ({center_in_screen_blue[0]}, {center_in_screen_blue[1]}, {depth_value_blue})")

                        # 中心に青い点を描画
                        cv2.circle(output_img, center_blue, 5, (255, 0, 0), -1)  # 青い点を描画
                        
            # 赤と青のx軸の誤差を計算
            if largest_contour_red is not None:
                if largest_contour_blue is not None:
                    x_diff = abs(center_red[0] - center_blue[0])
                    if x_diff <= 40:
                        # 黄色で両方の領域を囲む
                        combined_rect = cv2.boundingRect(np.concatenate((largest_contour_red, largest_contour_blue)))
                        cv2.rectangle(output_img, combined_rect, (0, 255, 255), 2)  # 黄色の矩形を描画

                        # 黄色の矩形の中心を計算
                        center_combined = (combined_rect[0] + combined_rect[2] // 2,
                                        combined_rect[1] + combined_rect[3] // 2)

                        # (0, 0) を中心にし、Y軸を逆にした座標系に変換
                        center_in_screen_center_combined = (center_combined[0] - center_offset[0], center_offset[1] - center_blue[1])


                        # 中心に黄色い点を描画
                        cv2.circle(output_img, center_combined, 5, (0, 255, 255), -1)  # 黄色い点を描画
                        # 黄色点の座標を出力
                        print(f"敵 Center: ({center_in_screen_center_combined[0]}, {center_in_screen_center_combined[1]})")

                    

            # FPSを計算
            curr_time = time.time()
            elapsed_time = curr_time - prev_time
            frame_count += 1
            if elapsed_time >= 0.1:
                fps = frame_count / elapsed_time
                frame_count = 0
                prev_time = curr_time

                # FPSをコンソールに表示
                #print(f"FPS: {fps:.2f}")

                # FPSを画像に表示
                #cv2.putText(output_img, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

            # 結果を表示
            cv2.imshow("Depth Frame", depth_img)  # 深度フレームを表示
            cv2.imshow("Masked Result", output_img)  # 最大の赤色と青色領域を強調した結果を表示

            if cv2.waitKey(1) >= 0:
                break  # キーが押されたらループを終了

    finally:
        # パイプラインを停止
        pipeline.stop()
        cv2.destroyAllWindows()  # OpenCVウィンドウを閉じる

if __name__ == "__main__":
    main()
