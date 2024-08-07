import sensor, image, time
import pyb
import random

# 设置相机
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

pyb.LED(1).on()  # 红色 LED
pyb.LED(2).on()  # 绿色 LED
pyb.LED(3).on()  # 蓝色 LED


# 初始化UART1，波特率为115200
uart = pyb.UART(3,115200, bits=8, parity=None, stop=1, timeout_char=1000)  # 使用UART1，波特率115200


# 定义颜色阈值
green_threshold = (0, 45, 69, -33, 27, -41)  # 适用于绿色底色
black_threshold = (0, 25, 39, -33, 85, -30)  # 适用于黑色棋子
white_threshold = (100, 68, 15, -25, 33, -24) # 适用于白色棋子

# 内边距参数
padding = 15  # 缩小识别范围的边距

# 棋格坐标到标号的映射
coords_to_pos = {
    (0, 0): 1, (0, 1): 2, (0, 2): 3,
    (1, 0): 4, (1, 1): 5, (1, 2): 6,
    (2, 0): 7, (2, 1): 8, (2, 2): 9
}

# 初始化棋盘信息数组  二维
board_state = [[0 for _ in range(3)] for _ in range(3)]



board = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # 空棋盘 一维
start_time = time.time()
timeout = 2  # 超时时间（秒）

buffer = [0,0]
# 循环次数初始化

circulate=0

def reset_uart():
    global uart
    uart.deinit()
    time.sleep(2)
    uart = pyb.UART(3,115200, bits=8, parity=None, stop=1, timeout_char=1000)  # 使用UART1，波特率115200


# 对弈策略函数
def find_best_move(board, player):
    opponent = 1 if player == 2 else 2

    # 优先级函数
    def priority_move(move):
        if board[move] != 0:
            return -1  # 无效位置

        # 检查是否有赢棋
        board[move] = player
        if is_winner(board, player):
            board[move] = 0
            return 4  # 赢棋优先级最高
        board[move] = 0

        # 检查是否需要阻挡对手赢棋
        board[move] = opponent
        if is_winner(board, opponent):
            board[move] = 0
            return 3  # 阻挡对手赢棋优先级次之
        board[move] = 0

        # 占中
        if move == 4:
            return 2  # 中心优先级第三

        # 占角
        if move in [0, 2, 6, 8]:
            return 1  # 角优先级第四

        # 占边
        if move in [1, 3, 5, 7]:
            return 0  # 边优先级最低

    # 获取所有可能的移动及其优先级
    possible_moves = [(move, priority_move(move)) for move in range(9)]
    # 过滤掉无效位置
    possible_moves = [move for move in possible_moves if move[1] != -1]
    # 按优先级排序
    possible_moves.sort(key=lambda x: x[1], reverse=True)

    # 返回优先级最高的移动
    return possible_moves[0][0] + 1 if possible_moves else -1




def is_winner(board, player):
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # 行
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # 列
        [0, 4, 8], [2, 4, 6]              # 对角线
    ]
    for condition in win_conditions:
        if all(board[i] == player for i in condition):
            return True
    return False

def print_board(board):
    symbols = {0: ' ', 1: 'O', 2: 'X'}
    for i in range(3):
        row = [symbols[board[j]] for j in range(i*3, (i+1)*3)]
        print("|".join(row))
        if i < 2:
            print("-----")

def is_board_full(board):
    return all(cell != 0 for cell in board)



# 二维数组转化为一维数组方便进行计算
def convert_to_1d(board_2d):
    """将二维数组转换为一维数组"""
    return [cell for row in board_2d for cell in row]

















# 串口发送函数
def send_chessboard_info(uart, chessboard):
    # 将棋盘信息转换为字符串，方便传输
    info_str = ''.join(str(cell) for row in chessboard for cell in row)

    # 发送字符串信息给STM32
    uart.write(info_str + '\n')


# 调试函数  方便调试阶段使用
def debugging():
    while(True):

        img = sensor.snapshot()

        # 查找绿色区域（棋盘底色）
        green_blobs = img.find_blobs([green_threshold], pixels_threshold=200, area_threshold=200, merge=True)
        if len(green_blobs) > 0:
            # 找到最大的绿色区域，假设为棋盘区域
            green_blob = max(green_blobs, key=lambda b: b.pixels())
            x, y, w, h = green_blob.rect()

            # 绘制绿色区域的边界
            img.draw_rectangle(green_blob.rect(), color=(0, 255, 0))

            # 将棋盘区域划分为9个区域
            cell_width = w // 3
            cell_height = h // 3

            for row in range(3):
                for col in range(3):
                    cell_x = x + col * cell_width
                    cell_y = y + row * cell_height
                    cell_w = cell_width
                    cell_h = cell_height

                    # 绘制每个棋格的边界
                    img.draw_rectangle(cell_x, cell_y, cell_w, cell_h, color=(0, 0, 255))

                    # 缩小识别范围
                    inner_cell_x = cell_x + padding
                    inner_cell_y = cell_y + padding
                    inner_cell_w = cell_w - 2 * padding
                    inner_cell_h = cell_h - 2 * padding

                    # 从图像中提取当前棋格的缩小区域
                    cell_img = img.copy(roi=(inner_cell_x, inner_cell_y, inner_cell_w, inner_cell_h))

                    # 获取当前棋格的标号
                    cell_pos = coords_to_pos[(row, col)]

                    # 初始化当前棋格状态为空
                    cell_state = 0

                    # 在每个棋格中查找黑色物体
                    black_blobs = cell_img.find_blobs([black_threshold], pixels_threshold=50, area_threshold=50)
                    if black_blobs:
                        for blob in black_blobs:
                            img.draw_rectangle(inner_cell_x + blob.rect()[0], inner_cell_y + blob.rect()[1], blob.rect()[2], blob.rect()[3], color=(0, 0, 0))
                            img.draw_cross(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), color=(0, 0, 0))
                            img.draw_string(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), "Black", color=(0, 0, 0))
                            #print("Black piece found in cell {}".format(cell_pos))
                            cell_state = 2
                            break  # 由于一个格子中最多只能有一个棋子，找到后跳出循环

                    # 在每个棋格中查找白色物体
                    white_blobs = cell_img.find_blobs([white_threshold], pixels_threshold=50, area_threshold=50)
                    if white_blobs:
                        for blob in white_blobs:
                            img.draw_rectangle(inner_cell_x + blob.rect()[0], inner_cell_y + blob.rect()[1], blob.rect()[2], blob.rect()[3], color=(255, 255, 255))
                            img.draw_cross(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), color=(255, 255, 255))
                            img.draw_string(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), "White", color=(255, 255, 255))
                            #print("White piece found in cell {}".format(cell_pos))
                            cell_state = 1
                            break  # 由于一个格子中最多只能有一个棋子，找到后跳出循环

                    # 更新棋盘信息数组
                    board_state[row][col] = cell_state

        for row in board_state:
            print(row)
        send_chessboard_info(uart, board_state)
        circulate = circulate +1

        # 调试时拍摄的次数
        if (circulate == 1000):
            circulate = 0
            break



# 将识别到的棋盘情况存储在board_state中
def get_chess_state():
    global circulate
    while(True):
        img = sensor.snapshot()

        # 查找绿色区域（棋盘底色）
        green_blobs = img.find_blobs([green_threshold], pixels_threshold=200, area_threshold=200, merge=True)
        if len(green_blobs) > 0:
            # 找到最大的绿色区域，假设为棋盘区域
            green_blob = max(green_blobs, key=lambda b: b.pixels())
            x, y, w, h = green_blob.rect()

            # 绘制绿色区域的边界
            img.draw_rectangle(green_blob.rect(), color=(0, 255, 0))

            # 将棋盘区域划分为9个区域
            cell_width = w // 3
            cell_height = h // 3

            for row in range(3):
                for col in range(3):
                    cell_x = x + col * cell_width
                    cell_y = y + row * cell_height
                    cell_w = cell_width
                    cell_h = cell_height

                    # 绘制每个棋格的边界
                    img.draw_rectangle(cell_x, cell_y, cell_w, cell_h, color=(0, 0, 255))

                    # 缩小识别范围
                    inner_cell_x = cell_x + padding
                    inner_cell_y = cell_y + padding
                    inner_cell_w = cell_w - 2 * padding
                    inner_cell_h = cell_h - 2 * padding

                    # 从图像中提取当前棋格的缩小区域
                    cell_img = img.copy(roi=(inner_cell_x, inner_cell_y, inner_cell_w, inner_cell_h))

                    # 获取当前棋格的标号
                    cell_pos = coords_to_pos[(row, col)]

                    # 初始化当前棋格状态为空
                    cell_state = 0

                    # 在每个棋格中查找黑色物体
                    black_blobs = cell_img.find_blobs([black_threshold], pixels_threshold=50, area_threshold=50)
                    if black_blobs:
                        for blob in black_blobs:
                            img.draw_rectangle(inner_cell_x + blob.rect()[0], inner_cell_y + blob.rect()[1], blob.rect()[2], blob.rect()[3], color=(0, 0, 0))
                            img.draw_cross(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), color=(0, 0, 0))
                            img.draw_string(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), "Black", color=(0, 0, 0))
                            #print("Black piece found in cell {}".format(cell_pos))
                            cell_state = 2
                            break  # 由于一个格子中最多只能有一个棋子，找到后跳出循环

                    # 在每个棋格中查找白色物体
                    white_blobs = cell_img.find_blobs([white_threshold], pixels_threshold=50, area_threshold=50)
                    if white_blobs:
                        for blob in white_blobs:
                            img.draw_rectangle(inner_cell_x + blob.rect()[0], inner_cell_y + blob.rect()[1], blob.rect()[2], blob.rect()[3], color=(255, 255, 255))
                            img.draw_cross(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), color=(255, 255, 255))
                            img.draw_string(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), "White", color=(255, 255, 255))
                            #print("White piece found in cell {}".format(cell_pos))
                            cell_state = 1
                            break  # 由于一个格子中最多只能有一个棋子，找到后跳出循环

                    # 更新棋盘信息数组
                    board_state[row][col] = cell_state
        circulate += 1
        return board_state
        # 打印棋盘状态数组
        if (circulate == 1):
            break




while(True):
    board_state=get_chess_state()
    board = convert_to_1d(board_state)
    win1 = is_winner(board,2)
    #win2 = is_winner(board,1)
    print(win1)
    #print(win2)
    if (win1):
        buffer=[1,1]
        key = chr (0)
        uart.write(buffer)
    else:
        best_move = find_best_move(board, 2)
        #best_move_char = chr(best_move)
        if 0 <= best_move < 0x110000:
            best_move_char = chr(best_move)
        else:
            best_move_char = '12'  # 使用默认值或处理无效字符

        print(best_move)

        buffer=[0,best_move]
        data_to_send = '0' + best_move_char + '\n'
        buffer_bytes = bytearray(buffer)
        send_chessboard_info(uart, buffer)
        # 发送数据
        #uart.write(buffer_bytes)
        print(buffer)
        #print(buffer_bytes)
        uart.deinit()
        reset_uart()







#while(True):
    #board_state=get_chess_state()
    #board = convert_to_1d(board_state)
    #win1 = is_winner(board,2)
    ##win2 = is_winner(board,1)
    #print(win1)
    ##print(win2)
    #if (win1):
        #key =  '1'
        #uart.write('0' + key + '\n')
    #else:
        #best_move = find_best_move(board, 2)+48
        ##best_move_char = chr(best_move)
        #if 0 <= best_move < 0x110000:
            #best_move_char = chr(best_move)
        #else:
            #best_move_char = '12'  # 使用默认值或处理无效字符

        #print(best_move)
        #print(best_move_char)

        #data_to_send = '0' + best_move_char + '\n'
        #uart.write(data_to_send.encode())
        #print(f"Sending data: {data_to_send.encode()}")
        ## 打印发送的内容
        #print(data_to_send)
        ##uart.write('0' + best_move_char+'\n')
        ##uart.write(buffer)
        ##send_chessboard_info(uart, buffer)
        ## 关闭串口
        ##uart.deinit()
        ##reset_uart()




while(True):

    if uart.any():
    # 读取可用数据
        data = uart.read()
        print(data)
        if (data == b'4'):

            board_state=get_chess_state()
            board = convert_to_1d(board_state)
            win1 = is_winner(board,2)
            #win2 = is_winner(board,1)
            print(win1)
            #print(win2)
            if (win1):
                buffer=[1,1]
                key = chr (0)
                uart.write(buffer)
            else:
                best_move = find_best_move(board, 2)
                #best_move_char = chr(best_move)
                if 0 <= best_move < 0x110000:
                    best_move_char = chr(best_move)
                else:
                    best_move_char = '12'  # 使用默认值或处理无效字符

                print(best_move)

                buffer=[0,best_move]
                data_to_send = '0' + best_move_char + '\n'

                print(buffer)

                uart.deinit()
                reset_uart()
                while(True):

                    if uart.any():
                    # 读取可用数据
                        data = uart.read()
                        print(data)
                        if (data == b'4'):

                            board_state=get_chess_state()
                            board = convert_to_1d(board_state)
                            win1 = is_winner(board,2)
                            #win2 = is_winner(board,1)
                            print(win1)
                            #print(win2)
                            if (win1):
                                key = chr (0)
                                uart.write('0' + key + '\n')
                            else:
                                best_move = find_best_move(board, 2)+48
                                #best_move_char = chr(best_move)
                                if 0 <= best_move < 0x110000:
                                    best_move_char = chr(best_move)
                                else:
                                    best_move_char = '12'  # 使用默认值或处理无效字符

                                print(best_move)



                                data_to_send = '0' + best_move_char + '\n'
                                uart.write(data_to_send.encode())
                                print(f"Sending data: {data_to_send.encode()}")
                                # 关闭串口
                                uart.deinit()
                                reset_uart()



                #time.sleep(10)

        if (data == b'5'):

            board_state=get_chess_state()
            board = convert_to_1d(board_state)
            win1 = is_winner(board,1)
            #win2 = is_winner(board,1)
            print(win1)
            #print(win2)
            if (win1):
                key = chr (0)
                uart.write('0' + key + '\n')
            else:
                best_move = find_best_move(board, 1)
                best_move_char = chr(best_move)
                print(best_move)
                buffer = '0' + best_move_char + '\n'
                uart.write(buffer)
                while(True):
                    uart.write(buffer)
                    break
































#while(True):

    #img = sensor.snapshot()

    ## 查找绿色区域（棋盘底色）
    #green_blobs = img.find_blobs([green_threshold], pixels_threshold=200, area_threshold=200, merge=True)
    #if len(green_blobs) > 0:
        ## 找到最大的绿色区域，假设为棋盘区域
        #green_blob = max(green_blobs, key=lambda b: b.pixels())
        #x, y, w, h = green_blob.rect()

        ## 绘制绿色区域的边界
        #img.draw_rectangle(green_blob.rect(), color=(0, 255, 0))

        ## 将棋盘区域划分为9个区域
        #cell_width = w // 3
        #cell_height = h // 3

        #for row in range(3):
            #for col in range(3):
                #cell_x = x + col * cell_width
                #cell_y = y + row * cell_height
                #cell_w = cell_width
                #cell_h = cell_height

                ## 绘制每个棋格的边界
                #img.draw_rectangle(cell_x, cell_y, cell_w, cell_h, color=(0, 0, 255))

                ## 缩小识别范围
                #inner_cell_x = cell_x + padding
                #inner_cell_y = cell_y + padding
                #inner_cell_w = cell_w - 2 * padding
                #inner_cell_h = cell_h - 2 * padding

                ## 从图像中提取当前棋格的缩小区域
                #cell_img = img.copy(roi=(inner_cell_x, inner_cell_y, inner_cell_w, inner_cell_h))

                ## 获取当前棋格的标号
                #cell_pos = coords_to_pos[(row, col)]

                ## 初始化当前棋格状态为空
                #cell_state = 0

                ## 在每个棋格中查找黑色物体
                #black_blobs = cell_img.find_blobs([black_threshold], pixels_threshold=50, area_threshold=50)
                #if black_blobs:
                    #for blob in black_blobs:
                        #img.draw_rectangle(inner_cell_x + blob.rect()[0], inner_cell_y + blob.rect()[1], blob.rect()[2], blob.rect()[3], color=(0, 0, 0))
                        #img.draw_cross(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), color=(0, 0, 0))
                        #img.draw_string(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), "Black", color=(0, 0, 0))
                        ##print("Black piece found in cell {}".format(cell_pos))
                        #cell_state = 2
                        #break  # 由于一个格子中最多只能有一个棋子，找到后跳出循环

                ## 在每个棋格中查找白色物体
                #white_blobs = cell_img.find_blobs([white_threshold], pixels_threshold=50, area_threshold=50)
                #if white_blobs:
                    #for blob in white_blobs:
                        #img.draw_rectangle(inner_cell_x + blob.rect()[0], inner_cell_y + blob.rect()[1], blob.rect()[2], blob.rect()[3], color=(255, 255, 255))
                        #img.draw_cross(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), color=(255, 255, 255))
                        #img.draw_string(inner_cell_x + blob.cx(), inner_cell_y + blob.cy(), "White", color=(255, 255, 255))
                        ##print("White piece found in cell {}".format(cell_pos))
                        #cell_state = 1
                        #break  # 由于一个格子中最多只能有一个棋子，找到后跳出循环

                ## 更新棋盘信息数组
                #board_state[row][col] = cell_state

    ## 打印棋盘状态数组
    #print("Board state:")
    #for row in board_state:
        #print(row)
    ##time.sleep(1)
    #send_chessboard_info(uart, board_state)












