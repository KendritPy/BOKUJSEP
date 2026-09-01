#include <pspkernel.h>
#include <pspctrl.h>
#include <pspiofilemgr.h>
#include <string.h>

#define MODULE_NAME "BokuLangToggle"
#define LOG_PATH "ms0:/PSP/PLUGINS/BokuLangToggle/BokuLangToggle.log"
#define CONFIG_PATH "ms0:/PSP/PLUGINS/BokuLangToggle/BokuLangToggle.ini"

PSP_MODULE_INFO(MODULE_NAME, PSP_MODULE_USER, 0, 1);
PSP_MAIN_THREAD_ATTR(PSP_THREAD_ATTR_USER);

enum BokuLanguage {
    BOKU_LANG_JP = 0,
    BOKU_LANG_ES = 1
};

static volatile int g_running = 1;
static volatile enum BokuLanguage g_language = BOKU_LANG_ES;
static SceUID g_input_thread = -1;

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

void SetLanguage(enum BokuLanguage language)
{
    if (language != BOKU_LANG_JP && language != BOKU_LANG_ES)
        return;
    if (g_language == language)
        return;
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
    char data[256];
    int length;
    SceUID fd = sceIoOpen(CONFIG_PATH, PSP_O_RDONLY, 0);
    if (fd < 0)
        return;
    length = sceIoRead(fd, data, sizeof(data) - 1);
    sceIoClose(fd);
    if (length <= 0)
        return;
    data[length] = '\0';
    if (strstr(data, "DefaultLanguage=JP") != NULL)
        g_language = BOKU_LANG_JP;
    else if (strstr(data, "DefaultLanguage=ES") != NULL)
        g_language = BOKU_LANG_ES;
}

static int InputThread(SceSize args, void *argp)
{
    SceCtrlData pad;
    unsigned int previous = 0;
    (void)args;
    (void)argp;

    /* Peek only. Do not change the game's controller sampling mode/cycle. */
    while (g_running) {
        unsigned int current;
        memset(&pad, 0, sizeof(pad));
        sceCtrlPeekBufferPositive(&pad, 1);
        current = pad.Buttons & PSP_CTRL_NOTE;
        if (current && !previous)
            ToggleLanguage();
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
    LogLine("[BokuLang] Plugin loaded");
    LogLine("[BokuLang] Game UCJS10038 selected by plugin.ini");
    LoadConfiguration();
    LogLine(g_language == BOKU_LANG_JP
        ? "[BokuLang] initial language JP"
        : "[BokuLang] initial language ES");
    LogLine("[BokuLang] milestone-zero build: dialogue hook disabled safely");

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

    LogLine("[BokuLang] input thread active; guest Note toggles language");
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
