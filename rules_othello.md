# LUẬT CHƠI OTHELLO / REVERSI

## 1. MỤC TIÊU
- Trò chơi dành cho 2 người: Đen và Trắng.
- Mục tiêu là kết thúc ván với số quân của mình nhiều hơn đối thủ.

## 2. BÀN CỜ BAN ĐẦU
- Bàn cờ tiêu chuẩn có 8 hàng x 8 cột (64 ô).
- Ban đầu có 4 quân ở chính giữa: 2 quân Đen và 2 quân Trắng nằm xen kẽ theo đường chéo.
- 60 ô còn lại để trống.
- Theo luật phổ biến, Đen đi trước.

## 3. NƯỚC ĐI HỢP LỆ
- Chỉ được đặt quân vào ô trống.
- Nước đi hợp lệ phải kẹp được ít nhất 1 quân đối thủ giữa quân vừa đặt và một quân cùng màu đã có trên bàn.
- Kiểm tra theo 8 hướng: ngang, dọc và chéo.
- Các quân bị kẹp phải liên tiếp nhau; không được có ô trống xen giữa.
- Nếu không lật được quân đối thủ nào thì nước đi không hợp lệ.

## 4. LẬT QUÂN
- Sau khi đặt quân hợp lệ, phải lật tất cả quân đối thủ bị kẹp theo mọi hướng hợp lệ.
- Một nước đi có thể lật quân theo nhiều hướng cùng lúc.
- Không được tự chọn chỉ lật một phần số quân bị kẹp.
- Quân đã đặt không di chuyển sang ô khác; quân chỉ đổi màu khi bị lật.

## 5. LUÂN PHIÊN VÀ BỎ LƯỢT
- Hai người chơi lần lượt đi.
- Nếu còn ít nhất một nước đi hợp lệ, người chơi bắt buộc phải đi, không được bỏ lượt tùy ý.
- Chỉ được bỏ lượt khi không còn nước đi hợp lệ nào.
- Nếu một người phải bỏ lượt, người còn lại tiếp tục đi nếu có nước hợp lệ.

## 6. KẾT THÚC VÁN
**Ván cờ kết thúc khi:**
- Bàn cờ đã kín; hoặc
- Cả hai người chơi đều không còn nước đi hợp lệ, dù vẫn còn ô trống.

**Khi kết thúc, đếm số quân:**
- Đen nhiều hơn: Đen thắng.
- Trắng nhiều hơn: Trắng thắng.
- Bằng nhau: Hòa.
Lưu ý: Một số giải đấu có quy định tính điểm riêng; cần thống nhất nếu triển khai theo luật giải đấu.

## 7. CÁC LỖI CẦN TRÁNH
- Đặt quân lên ô đã có quân.
- Đặt quân mà không kẹp được quân đối thủ.
- Nhảy qua ô trống hoặc quân cùng màu để kẹp quân.
- Bỏ lượt dù vẫn còn nước hợp lệ.
- Chỉ lật một phần quân bị kẹp.
- Chỉ kiểm tra người chơi hiện tại khi xác định kết thúc; phải kiểm tra cả hai bên.

## 8. CHECKLIST KHI LẬP TRÌNH
[ ] Khởi tạo bàn 8x8 và 4 quân ở giữa.

[ ] Kiểm tra nước đi theo 8 hướng.

[ ] Đặt quân và lật tất cả quân bị kẹp.

[ ] Chuyển lượt đúng.

[ ] Xử lý bỏ lượt khi không có nước hợp lệ.

[ ] Kết thúc khi bàn đầy hoặc cả hai bên không thể đi.

[ ] Đếm quân và xác định thắng/thua/hòa.

[ ] Kiểm thử nước đi ở góc, cạnh, nhiều hướng và tình huống bỏ lượt.

**TÓM TẮT:**
Đen đi trước. Mỗi lượt đặt quân vào ô trống sao cho kẹp được ít nhất một quân đối thủ theo một trong 8 hướng, rồi lật tất cả quân bị kẹp. Không có nước hợp lệ thì phải bỏ lượt. Khi cả hai bên đều không thể đi hoặc bàn cờ đầy, đếm quân để xác định kết quả.
