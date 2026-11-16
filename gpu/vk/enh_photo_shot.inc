// (enhanced) Hookshot Enhanced photo mode: a photo at the picture's own size (enh_photo.h; docs/enhanced/PHOTO_MODE.md).
// Included by gpu/vk/vk_replay.cpp after shot_ask_take, in its namespace; do_present calls enh_photo_record after the control
// bridge's shot is recorded and enh_photo_take after its submit, as shot_ask_record and shot_ask_take. Unlike those shots
// (kShotW x kShotH, 1280x720 unless RX_VK_SHOT_W/H), the photo is the presented picture's crop at 1:1: 3440x1440 at a
// 21:9 output, so its shape is the picture's. Its image and readback buffer are made for the one photo and let go after.
// The pixels are the presented picture's as 8-bit RGBA: an HDR picture is not tone mapped for the PNG.

struct EnhPhoto {
    bool on = false;
    uint64_t value = 0;
    uint32_t w = 0, h = 0;
    VkImage image = VK_NULL_HANDLE;
    VmaAllocation image_alloc = nullptr, buf_alloc = nullptr;
    VkBuffer buf = VK_NULL_HANDLE;
    void* map = nullptr;
};
EnhPhoto enh_photo;   // (replay_mu, as shot_asked)

void enh_photo_record(VkCommandBuffer cmd, VkImage src, uint32_t sw, uint32_t sh, const int crop[4], uint64_t value) {
    enh_photo_keys();
    if (enh_photo.on || !src || !enh_photo_take_ask()) return;
    const PresentSourceRect source = present_source_rect(sw, sh, crop);
    if (!source.w || !source.h) return;
    EnhPhoto p;
    p.w = source.w, p.h = source.h;
    VkImageCreateInfo ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    ci.imageType = VK_IMAGE_TYPE_2D;
    ci.format = VK_FORMAT_R8G8B8A8_UNORM;
    ci.extent = {p.w, p.h, 1};
    ci.mipLevels = ci.arrayLayers = 1;
    ci.samples = VK_SAMPLE_COUNT_1_BIT;
    ci.usage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    if (!create_image(ci, p.image, p.image_alloc)) {
        enh_photo_written("(no image for the photo)", false);
        return;
    }
    if (!create_buffer((uint64_t)p.w * p.h * 4, VK_BUFFER_USAGE_TRANSFER_DST_BIT, true, p.buf, p.buf_alloc, &p.map)) {
        destroy_image(p.image, p.image_alloc);
        enh_photo_written("(no buffer for the photo)", false);
        return;
    }
    image_barrier(cmd, p.image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
    blit_crop(cmd, src, sw, sh, crop, p.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, p.w, p.h);
    image_barrier(cmd, p.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
    const VkBufferImageCopy c{0, 0, 0, {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1}, {0, 0, 0}, {p.w, p.h, 1}};
    vkCmdCopyImageToBuffer(cmd, p.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, p.buf, 1, &c);
    capture_host_read_barrier(cmd, p.buf, (VkDeviceSize)p.w * p.h * 4);
    p.on = true, p.value = value;
    enh_photo = p;
}

/// The photo read back once the GPU is past it (never waited for), written as a PNG on a thread of its own
void enh_photo_take() {
    if (!enh_photo.on || completed() < enh_photo.value) return;
    EnhPhoto p = enh_photo;
    enh_photo = EnhPhoto{};
    invalidate_mapped(p.buf_alloc, (uint64_t)p.w * p.h * 4);
    auto px = std::make_shared<std::vector<uint8_t>>((const uint8_t*)p.map, (const uint8_t*)p.map + (size_t)p.w * p.h * 4);
    destroy_buffer(p.buf, p.buf_alloc);
    destroy_image(p.image, p.image_alloc);
    std::thread([px, w = p.w, h = p.h] {
        for (size_t i = 3; i < px->size(); i += 4) (*px)[i] = 255;   // (the picture's alpha is no transparency)
        const std::string dir = enh_photo_folder();
        std::error_code ec;
        std::filesystem::create_directories(std::filesystem::path(dir), ec);
        const auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
        std::tm tm{};
#ifdef _WIN32
        localtime_s(&tm, &now);
#else
        localtime_r(&now, &tm);
#endif
        char name[64];
        strftime(name, sizeof name, ENH_PRODUCT "_%Y%m%d_%H%M%S", &tm);
#ifdef _WIN32
        const char sep = '\\';
#else
        const char sep = '/';
#endif
        std::string path = dir + sep + name + ".png";
        for (int n = 2; std::filesystem::exists(std::filesystem::path(path), ec); n++)   // (two in one second)
            path = dir + sep + name + "_" + std::to_string(n) + ".png";
        const std::string part = path + ".part";
        bool ok = write_png(part.c_str(), px->data(), w, h);
        if (ok) ok = std::rename(part.c_str(), path.c_str()) == 0;
        if (!ok) std::remove(part.c_str());
        enh_photo_written(path, ok);
    }).detach();
}
