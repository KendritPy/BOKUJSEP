#include <pspkernel.h>
#include <pspctrl.h>
#include <pspiofilemgr.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define BOKU_CTRL_L3 0x0002u
#define BOKU_CTRL_R3 0x0004u
#define BOKU_CTRL_L2 0x0400u
#define BOKU_CTRL_R2 0x0800u

#define MODULE_NAME "BokuLangToggle"
#define LOG_PATH "ms0:/PSP/PLUGINS/BokuLangToggle/BokuLangToggle.log"
#define CONFIG_PATH "ms0:/PSP/PLUGINS/BokuLangToggle/BokuLangToggle.ini"
#define BLOB_PATH "ms0:/PSP/PLUGINS/BokuLangToggle/dialogue_blob.bin"
#define JP_ATLAS_PATH "ms0:/PSP/PLUGINS/BokuLangToggle/jp_atlas0.pim"
#define ES_ATLAS_PATH "ms0:/PSP/PLUGINS/BokuLangToggle/es_atlas0.pim"

#define DIALOGUE_CALL_ADDRESS 0x0881AE98u
#define DIALOGUE_CALL_WORD 0x0E206F87u
#define DIALOGUE_WALKER_ADDRESS 0x0881BE1Cu
#define WIDTH_LOAD_ADDRESS 0x0891B5D4u
#define WIDTH_ES_WORD 0x80B60000u
#define WIDTH_JP_WORD 0x24160010u
#define ATLAS_SIZE 131200u
#define FLAG_PAGE_COUNT_MISMATCH 2u
#define PAGE_CAPACITY 16u

typedef struct __attribute__((packed)) BlobHeader {
    char magic[4];
    uint32_t version;
    uint32_t count;
    uint32_t entry_size;
    uint32_t payload_offset;
    unsigned char digest[32];
} BlobHeader;

typedef struct __attribute__((packed)) BlobEntry {
    uint64_t identity;
    uint32_t es_offset;
    uint32_t jp_offset;
    uint32_t context_offset;
    uint32_t es_text_offset;
    uint32_t es_size;
    uint32_t jp_size;
    uint16_t context_size;
    uint16_t dialog_id;
    uint16_t block_index;
    uint16_t element_index;
    uint16_t flags;
} BlobEntry;

typedef int (*DialogueWalker)(uintptr_t, uintptr_t, uintptr_t, uintptr_t);

PSP_MODULE_INFO(MODULE_NAME, PSP_MODULE_USER, 0, 1);
PSP_MAIN_THREAD_ATTR(PSP_THREAD_ATTR_USER);

enum BokuLanguage {
    BOKU_LANG_JP = 0,
    BOKU_LANG_ES = 1
};

static volatile int g_running = 1;
static volatile enum BokuLanguage g_language = BOKU_LANG_ES;
static SceUID g_input_thread = -1;
static unsigned char *g_blob = NULL;
static SceUID g_blob_block = -1;
static SceUID g_jp_atlas_block = -1;
static SceUID g_es_atlas_block = -1;
static unsigned int g_blob_size = 0;
static BlobHeader *g_header = NULL;
static BlobEntry *g_entries = NULL;
static unsigned char *g_payload = NULL;
static unsigned char *g_jp_atlas = NULL;
static unsigned char *g_es_atlas = NULL;
static unsigned char *g_live_atlas = NULL;
static const unsigned char *g_cached_es = NULL;
static const unsigned char *g_cached_jp = NULL;
static unsigned char g_cached_prefix[8];
static unsigned int g_cached_prefix_size = 0;
static int g_hook_ready = 0;
static int g_hook_installed = 0;
static unsigned int g_toggle_mask = PSP_CTRL_NOTE;
static const char *g_toggle_button_name = "NOTE";

static int SetJapaneseRenderState(int japanese);

typedef struct ToggleButtonName {
    const char *name;
    unsigned int mask;
} ToggleButtonName;

static const ToggleButtonName g_toggle_buttons[] = {
    { "SELECT", PSP_CTRL_SELECT },
    { "START", PSP_CTRL_START },
    { "UP", PSP_CTRL_UP },
    { "RIGHT", PSP_CTRL_RIGHT },
    { "DOWN", PSP_CTRL_DOWN },
    { "LEFT", PSP_CTRL_LEFT },
    { "LTRIGGER", PSP_CTRL_LTRIGGER },
    { "L", PSP_CTRL_LTRIGGER },
    { "RTRIGGER", PSP_CTRL_RTRIGGER },
    { "R", PSP_CTRL_RTRIGGER },
    { "L2", BOKU_CTRL_L2 },
    { "L3", BOKU_CTRL_L3 },
    { "R2", BOKU_CTRL_R2 },
    { "R3", BOKU_CTRL_R3 },
    { "TRIANGLE", PSP_CTRL_TRIANGLE },
    { "CIRCLE", PSP_CTRL_CIRCLE },
    { "CROSS", PSP_CTRL_CROSS },
    { "SQUARE", PSP_CTRL_SQUARE },
    { "HOME", PSP_CTRL_HOME },
    { "HOLD", PSP_CTRL_HOLD },
    { "NOTE", PSP_CTRL_NOTE },
    { "SCREEN", PSP_CTRL_SCREEN },
    { "VOLUP", PSP_CTRL_VOLUP },
    { "VOL_UP", PSP_CTRL_VOLUP },
    { "VOLDOWN", PSP_CTRL_VOLDOWN },
    { "VOL_DOWN", PSP_CTRL_VOLDOWN },
    { "WLAN_UP", PSP_CTRL_WLAN_UP },
    { "WLAN", PSP_CTRL_WLAN_UP },
    { "REMOTE", PSP_CTRL_REMOTE },
    { "REMOTE_HOLD", PSP_CTRL_REMOTE },
    { "DISC", PSP_CTRL_DISC },
    { "MS", PSP_CTRL_MS },
    { "MEMSTICK", PSP_CTRL_MS }
};

static int TextEquals(const char *left, const char *right)
{
    while (*left && *right) {
        char a = *left++;
        char b = *right++;
        if (a >= 'a' && a <= 'z')
            a = (char)(a - 'a' + 'A');
        if (b >= 'a' && b <= 'z')
            b = (char)(b - 'a' + 'A');
        if (a != b)
            return 0;
    }
    return *left == '\0' && *right == '\0';
}

static int ReadConfigValue(const char *data, const char *key, char *value, unsigned int capacity)
{
    const char *line = data;
    unsigned int key_size = (unsigned int)strlen(key);
    if (capacity == 0)
        return 0;
    while (line && *line) {
        const char *end = strchr(line, '\n');
        const char *cursor;
        const char *value_end;
        unsigned int length;
        if (end == NULL)
            end = line + strlen(line);
        cursor = line;
        while (cursor < end && (*cursor == ' ' || *cursor == '\t' || *cursor == '\r'))
            ++cursor;
        if ((unsigned int)(end - cursor) >= key_size &&
            strncmp(cursor, key, key_size) == 0) {
            cursor += key_size;
            while (cursor < end && (*cursor == ' ' || *cursor == '\t'))
                ++cursor;
            if (cursor < end && *cursor == '=') {
                ++cursor;
                while (cursor < end && (*cursor == ' ' || *cursor == '\t'))
                    ++cursor;
                value_end = end;
                while (value_end > cursor &&
                       (value_end[-1] == ' ' || value_end[-1] == '\t' || value_end[-1] == '\r'))
                    --value_end;
                length = (unsigned int)(value_end - cursor);
                if (length >= capacity)
                    length = capacity - 1;
                memcpy(value, cursor, length);
                value[length] = '\0';
                return 1;
            }
        }
        line = *end ? end + 1 : NULL;
    }
    return 0;
}

static int ButtonMaskFromName(const char *name, unsigned int *mask, const char **canonical)
{
    unsigned int index;
    for (index = 0; index < sizeof(g_toggle_buttons) / sizeof(g_toggle_buttons[0]); ++index) {
        if (TextEquals(name, g_toggle_buttons[index].name)) {
            *mask = g_toggle_buttons[index].mask;
            *canonical = g_toggle_buttons[index].name;
            return 1;
        }
    }
    return 0;
}

static void LogLine(const char *text)
{
    SceUID fd = sceIoOpen(LOG_PATH, PSP_O_WRONLY | PSP_O_CREAT | PSP_O_APPEND, 0777);
    if (fd >= 0) {
        sceIoWrite(fd, text, strlen(text));
        sceIoWrite(fd, "\n", 1);
        sceIoClose(fd);
    }
}

enum BokuLanguage GetLanguage(void)
{
    return g_language;
}

static void LogValues(const char *label, unsigned int first, unsigned int second)
{
    char text[160];
    snprintf(text, sizeof(text), "[BokuLang] %s 0x%08X 0x%08X", label, first, second);
    LogLine(text);
}

static void ReleaseAssets(void)
{
    if (g_blob_block >= 0)
        sceKernelFreePartitionMemory(g_blob_block);
    if (g_jp_atlas_block >= 0)
        sceKernelFreePartitionMemory(g_jp_atlas_block);
    if (g_es_atlas_block >= 0)
        sceKernelFreePartitionMemory(g_es_atlas_block);
    g_blob_block = g_jp_atlas_block = g_es_atlas_block = -1;
    g_blob = g_jp_atlas = g_es_atlas = NULL;
    g_header = NULL;
    g_entries = NULL;
    g_payload = NULL;
    g_blob_size = 0;
}

static unsigned char *LoadFile(
    const char *path, const char *block_name, SceUID *block_out, unsigned int *size_out)
{
    SceUID fd;
    SceOff size;
    unsigned char *data;
    int read_size;
    fd = sceIoOpen(path, PSP_O_RDONLY, 0);
    if (fd < 0)
        return NULL;
    size = sceIoLseek(fd, 0, PSP_SEEK_END);
    sceIoLseek(fd, 0, PSP_SEEK_SET);
    if (size <= 0 || size > 0x01000000) {
        sceIoClose(fd);
        return NULL;
    }
    *block_out = sceKernelAllocPartitionMemory(
        2, block_name, PSP_SMEM_Low, (SceSize)size, NULL);
    if (*block_out < 0) {
        sceIoClose(fd);
        return NULL;
    }
    data = (unsigned char *)sceKernelGetBlockHeadAddr(*block_out);
    if (data == NULL) {
        sceKernelFreePartitionMemory(*block_out);
        *block_out = -1;
        sceIoClose(fd);
        return NULL;
    }
    read_size = sceIoRead(fd, data, (unsigned int)size);
    sceIoClose(fd);
    if (read_size != size) {
        sceKernelFreePartitionMemory(*block_out);
        *block_out = -1;
        return NULL;
    }
    *size_out = (unsigned int)size;
    return data;
}

static int LoadAssets(void)
{
    unsigned int jp_size = 0, es_size = 0;
    LogValues("pre-load code signatures",
        *(volatile uint32_t *)DIALOGUE_CALL_ADDRESS,
        *(volatile uint32_t *)WIDTH_LOAD_ADDRESS);
    g_blob = LoadFile(BLOB_PATH, "BokuLangBlob", &g_blob_block, &g_blob_size);
    g_jp_atlas = LoadFile(JP_ATLAS_PATH, "BokuLangJPAtlas", &g_jp_atlas_block, &jp_size);
    g_es_atlas = LoadFile(ES_ATLAS_PATH, "BokuLangESAtlas", &g_es_atlas_block, &es_size);
    if (g_blob == NULL || g_jp_atlas == NULL || g_es_atlas == NULL) {
        ReleaseAssets();
        return 0;
    }
    LogValues("assets loaded: blob/atlas bytes", g_blob_size, jp_size);
    LogValues("asset addresses blob/JP", (unsigned int)g_blob, (unsigned int)g_jp_atlas);
    LogValues("asset address ES/post-load call", (unsigned int)g_es_atlas,
        *(volatile uint32_t *)DIALOGUE_CALL_ADDRESS);
    LogValues("post-load width signature", *(volatile uint32_t *)WIDTH_LOAD_ADDRESS, 0);
    if (jp_size != ATLAS_SIZE || es_size != ATLAS_SIZE || g_blob_size < sizeof(BlobHeader)) {
        ReleaseAssets();
        return 0;
    }
    g_header = (BlobHeader *)g_blob;
    if (memcmp(g_header->magic, "BLT1", 4) != 0 || g_header->version != 2 ||
        g_header->entry_size != sizeof(BlobEntry) || g_header->count > 20000) {
        ReleaseAssets();
        return 0;
    }
    if (g_header->payload_offset < sizeof(BlobHeader) || g_header->payload_offset > g_blob_size ||
        sizeof(BlobHeader) + g_header->count * sizeof(BlobEntry) > g_header->payload_offset) {
        ReleaseAssets();
        return 0;
    }
    g_entries = (BlobEntry *)(g_blob + sizeof(BlobHeader));
    g_payload = g_blob + g_header->payload_offset;
    return 1;
}

static unsigned int PageOffsets(const unsigned char *raw, unsigned int size, unsigned int *offsets, unsigned int capacity)
{
    unsigned int count = 1, offset;
    offsets[0] = 0;
    for (offset = 0; offset + 5 < size; offset += 2) {
        uint16_t word, guard;
        memcpy(&word, raw + offset, 2);
        memcpy(&guard, raw + offset + 4, 2);
        if (word == 0x8002 && guard == 0 && count < capacity)
            offsets[count++] = offset + 4;
    }
    return count;
}

static const unsigned char *ResolveJapanese(const unsigned char *live)
{
    unsigned int index;
    const unsigned char *resolved = NULL;
    if (g_header == NULL || live == NULL || live < (const unsigned char *)0x08000000 ||
        live >= (const unsigned char *)0x0E000000)
        return NULL;
    if (g_cached_es == live && g_cached_jp != NULL && g_cached_prefix_size != 0 &&
        memcmp(live, g_cached_prefix, g_cached_prefix_size) == 0)
        return g_cached_jp;

    for (index = 0; index < g_header->count; ++index) {
        BlobEntry *entry = &g_entries[index];
        const unsigned char *es = g_payload + entry->es_offset;
        const unsigned char *jp = g_payload + entry->jp_offset;
        const unsigned char *context = g_payload + entry->context_offset;
        unsigned int es_pages[PAGE_CAPACITY], jp_pages[PAGE_CAPACITY], es_count, jp_count, page;
        es_count = PageOffsets(es, entry->es_size, es_pages, PAGE_CAPACITY);
        jp_count = PageOffsets(jp, entry->jp_size, jp_pages, PAGE_CAPACITY);
        for (page = 0; page < es_count; ++page) {
            const unsigned char *base;
            unsigned int suffix_size = entry->es_size - es_pages[page];
            /* A translated stream can have a different number of page
               controls. The live Spanish page still has an unambiguous
               ordinal, so use that ordinal when the original has one. */
            if (page >= jp_count)
                continue;
            if (memcmp(live, es + es_pages[page], suffix_size) != 0)
                continue;
            base = live - es_pages[page] - entry->es_text_offset;
            if (base < (const unsigned char *)0x08000000 ||
                base + entry->context_size >= (const unsigned char *)0x0E000000)
                continue;
            if (entry->context_size && memcmp(base, context, entry->context_size) != 0)
                continue;
            resolved = jp + jp_pages[page];
            goto found;
        }
    }
found:
    g_cached_es = live;
    g_cached_jp = resolved;
    g_cached_prefix_size = 8;
    memcpy(g_cached_prefix, live, g_cached_prefix_size);
    if (resolved != NULL)
        LogValues("resolved stream/page", (unsigned int)live, index);
    else
        LogValues("unresolved stream", (unsigned int)live, 0);
    return resolved;
}

static int DialogueWrapper(uintptr_t a0, uintptr_t a1, uintptr_t a2, uintptr_t a3)
{
    DialogueWalker original = (DialogueWalker)DIALOGUE_WALKER_ADDRESS;
    volatile uintptr_t *stream_field = (volatile uintptr_t *)(a1 + 0x54);
    uintptr_t original_stream = *stream_field;
    const unsigned char *replacement = NULL;
    static uintptr_t logged_stream = 0;
    static int logged_state = -1;
    int render_state = 0;
    int result;
    if (g_hook_ready && g_blob != NULL) {
        if (g_language == BOKU_LANG_JP)
            replacement = ResolveJapanese((const unsigned char *)original_stream);
        /* Apply the renderer on the game thread, paired with this stream.
           Keep fallback Spanish until the next call: GPU texture work may
           happen after the walker returns. Never change the requested mode. */
        render_state = replacement != NULL ? 1 : 0;
        if (!SetJapaneseRenderState(replacement != NULL)) {
            render_state = 2;
            replacement = NULL;
        }
        if (logged_stream != original_stream || logged_state != render_state) {
            LogValues("dialogue stream/requested language (0=JP,1=ES)",
                (unsigned int)original_stream, g_language);
            LogValues("dialogue render (0=ES,1=JP,2=font failure)/replacement",
                render_state, (unsigned int)replacement);
            logged_stream = original_stream;
            logged_state = render_state;
        }
    }
    if (replacement != NULL)
        *stream_field = (uintptr_t)replacement;
    result = original(a0, a1, a2, a3);
    if (replacement != NULL)
        *stream_field = original_stream;
    return result;
}

static unsigned char *FindLiveAtlas(void)
{
    uintptr_t address;
    uint32_t signature;
    memcpy(&signature, g_es_atlas, 4);
    /* The reversible proof measured atlas 0 through PPSSPP's uncached PSP
       alias at 0x0D37EC60. The cached mirror is not searchable from this PRX. */
    for (address = 0x0C800000; address + ATLAS_SIZE < 0x0DD00000; address += 16) {
        unsigned char *candidate = (unsigned char *)address;
        if (*(volatile uint32_t *)candidate == signature && memcmp(candidate, g_es_atlas, ATLAS_SIZE) == 0)
            return candidate;
    }
    return NULL;
}

static int SetJapaneseRenderState(int japanese)
{
    volatile uint32_t *width = (volatile uint32_t *)WIDTH_LOAD_ADDRESS;
    uint32_t replacement = japanese ? WIDTH_JP_WORD : WIDTH_ES_WORD;
    const unsigned char *wanted = japanese ? g_jp_atlas : g_es_atlas;
    const unsigned char *other = japanese ? g_es_atlas : g_jp_atlas;
    int needs_copy = 1;
    int state_changed = 0;
    /* PPSSPP can replace a compiled instruction with a 0x68xxxxxx JIT
       marker. Invalidate its block before checking or patching the word. */
    if (*width != WIDTH_ES_WORD && *width != WIDTH_JP_WORD)
        sceKernelIcacheInvalidateRange((void *)WIDTH_LOAD_ADDRESS, 4);
    if (*width != WIDTH_ES_WORD && *width != WIDTH_JP_WORD) {
        LogValues("ERROR unrecognized width instruction", *width, 0);
        return 0;
    }
    if (g_live_atlas != NULL) {
        if (memcmp(g_live_atlas, wanted, ATLAS_SIZE) == 0) {
            needs_copy = 0;
        } else if (memcmp(g_live_atlas, other, ATLAS_SIZE) != 0) {
            /* The game may have reloaded the font at another address during
               a scene change. Discard the old address and search again. */
            g_live_atlas = NULL;
        }
    }
    if (g_live_atlas == NULL) {
        LogLine("[BokuLang] scanning RAM for live Spanish atlas");
        g_live_atlas = FindLiveAtlas();
    }
    if (g_live_atlas == NULL) {
        LogLine("[BokuLang] ERROR live Spanish atlas not found");
        return 0;
    }
    if (needs_copy) {
        LogValues("live atlas", (unsigned int)g_live_atlas, japanese);
        if (memcmp(g_live_atlas, wanted, ATLAS_SIZE) == 0) {
            needs_copy = 0;
        } else if (memcmp(g_live_atlas, other, ATLAS_SIZE) != 0) {
            return 0;
        }
        if (needs_copy) {
            memcpy(g_live_atlas, wanted, ATLAS_SIZE);
            state_changed = 1;
        }
    }
    if (*width != replacement) {
        *width = replacement;
        state_changed = 1;
    }
    if (state_changed) {
        sceKernelDcacheWritebackAll();
        sceKernelIcacheClearAll();
    }
    if (needs_copy)
        LogLine(japanese
            ? "[BokuLang] Japanese atlas and fixed width active"
            : "[BokuLang] Spanish atlas and proportional width restored");
    return 1;
}

static int InstallDialogueHook(void)
{
    volatile uint32_t *call = (volatile uint32_t *)DIALOGUE_CALL_ADDRESS;
    uint32_t replacement, observed_call, observed_width;
    sceKernelIcacheInvalidateRange((void *)DIALOGUE_CALL_ADDRESS, 4);
    sceKernelIcacheInvalidateRange((void *)WIDTH_LOAD_ADDRESS, 4);
    /* Capture once before any logging syscall can yield to the game and let
       PPSSPP compile these instructions back into JIT markers. */
    observed_call = *call;
    observed_width = *(volatile uint32_t *)WIDTH_LOAD_ADDRESS;
    replacement = 0x0C000000u | ((((uintptr_t)&DialogueWrapper) >> 2) & 0x03FFFFFFu);
    LogValues("hook observed call/width", observed_call, observed_width);
    LogValues("hook expected original/installed", DIALOGUE_CALL_WORD, replacement);
    if (observed_call == replacement)
    {
        g_hook_installed = 1;
        return 1;
    }
    if (observed_call != DIALOGUE_CALL_WORD ||
        (observed_width != WIDTH_ES_WORD && observed_width != WIDTH_JP_WORD))
        return 0;
    *call = replacement;
    sceKernelDcacheWritebackAll();
    sceKernelIcacheClearAll();
    LogLine("[BokuLang] dialogue call hook installed/reinstalled");
    g_hook_installed = 1;
    return 1;
}

void SetLanguage(enum BokuLanguage language)
{
    if (language != BOKU_LANG_JP && language != BOKU_LANG_ES)
        return;
    if (g_language == language)
        return;
    LogLine(language == BOKU_LANG_JP
        ? "[BokuLang] toggle request ES -> JP"
        : "[BokuLang] toggle request JP -> ES");
    if (!g_hook_ready) {
        LogLine("[BokuLang] toggle ignored: dialogue hook is not ready");
        return;
    }
    /* Remember the request even between dialogue boxes, when no live font
       may exist. The next walker call applies text and font together. */
    if (language == BOKU_LANG_JP)
        LogLine("[BokuLang] language ES -> JP");
    else
        LogLine("[BokuLang] language JP -> ES");
    g_language = language;
}

void ToggleLanguage(void)
{
    SetLanguage(g_language == BOKU_LANG_JP ? BOKU_LANG_ES : BOKU_LANG_JP);
}

static void LoadConfiguration(void)
{
    char data[512];
    char value[32];
    unsigned int mask;
    const char *canonical;
    int length;
    SceUID fd = sceIoOpen(CONFIG_PATH, PSP_O_RDONLY, 0);
    if (fd < 0)
        return;
    length = sceIoRead(fd, data, sizeof(data) - 1);
    sceIoClose(fd);
    if (length <= 0)
        return;
    data[length] = '\0';
    if (ReadConfigValue(data, "DefaultLanguage", value, sizeof(value))) {
        if (TextEquals(value, "JP"))
            g_language = BOKU_LANG_JP;
        else if (TextEquals(value, "ES"))
            g_language = BOKU_LANG_ES;
    }
    if (ReadConfigValue(data, "ToggleButton", value, sizeof(value))) {
        if (ButtonMaskFromName(value, &mask, &canonical)) {
            g_toggle_mask = mask;
            g_toggle_button_name = canonical;
        } else {
            LogLine("[BokuLang] invalid ToggleButton; using NOTE");
        }
    }
}

static int InputThread(SceSize args, void *argp)
{
    SceCtrlData pad;
    unsigned int previous = 0;
    (void)args;
    (void)argp;

    /* Peek only. Do not change the game's controller sampling mode/cycle. */
    if (g_language == BOKU_LANG_JP && g_hook_ready) {
        g_hook_ready = 0;
        if (LoadAssets())
            g_hook_ready = 1;
        else
            LogLine("[BokuLang] ERROR initial JP assets unavailable; retry with toggle input");
    }
    while (g_running) {
        unsigned int current;
        memset(&pad, 0, sizeof(pad));
        sceCtrlPeekBufferPositive(&pad, 1);
        current = pad.Buttons & g_toggle_mask;
        if (current && !previous) {
            char text[128];
            snprintf(text, sizeof(text), "[BokuLang] guest %s toggle edge received", g_toggle_button_name);
            LogLine(text);
            g_hook_ready = 0;
            if (g_blob == NULL && !LoadAssets()) {
                g_hook_ready = 0;
                LogLine("[BokuLang] ERROR lazy runtime asset load failed");
            } else if (!InstallDialogueHook()) {
                g_hook_ready = 0;
                LogLine("[BokuLang] ERROR savestate hook recovery failed");
            } else {
                g_hook_ready = 1;
            }
            ToggleLanguage();
        }
        previous = current;
        sceKernelDelayThread(16000);
    }
    sceKernelExitDeleteThread(0);
    return 0;
}

int module_start(SceSize args, void *argp)
{
    int result;
    (void)args;
    (void)argp;

    g_running = 1;
    LogLine("[BokuLang] Plugin loaded: " __DATE__ " " __TIME__);
    LogLine("[BokuLang] Game UCJS10038 selected by plugin.ini");
    LoadConfiguration();
    LogLine(g_language == BOKU_LANG_JP
        ? "[BokuLang] initial language JP"
        : "[BokuLang] initial language ES");
    if (*(volatile uint32_t *)DIALOGUE_CALL_ADDRESS != DIALOGUE_CALL_WORD ||
               *(volatile uint32_t *)WIDTH_LOAD_ADDRESS != WIDTH_ES_WORD) {
        LogValues("startup signatures call/width",
            *(volatile uint32_t *)DIALOGUE_CALL_ADDRESS,
            *(volatile uint32_t *)WIDTH_LOAD_ADDRESS);
        LogLine("[BokuLang] ERROR executable signature mismatch; dialogue hook disabled");
    } else if (!InstallDialogueHook()) {
        LogLine("[BokuLang] ERROR startup call hook installation failed");
    } else {
        g_hook_ready = 1;
        LogLine("[BokuLang] startup gate installed; assets and JP resolution are lazy on toggle input");
    }

    g_input_thread = sceKernelCreateThread(
        "BokuLangInput", InputThread, 0x30, 0x2000, PSP_THREAD_ATTR_USER, NULL);
    if (g_input_thread < 0) {
        LogLine("[BokuLang] ERROR input thread creation failed");
        return 0;
    }

    result = sceKernelStartThread(g_input_thread, 0, NULL);
    if (result < 0) {
        LogLine("[BokuLang] ERROR input thread start failed");
        sceKernelDeleteThread(g_input_thread);
        g_input_thread = -1;
        return 0;
    }

    LogLine("[BokuLang] input thread active; configured guest button toggles language");
    return 0;
}

int module_stop(SceSize args, void *argp)
{
    (void)args;
    (void)argp;
    g_running = 0;
    LogLine("[BokuLang] Plugin stopping");
    return 0;
}
