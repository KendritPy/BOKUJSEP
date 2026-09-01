#include <pspkernel.h>

__attribute__((weak)) void abort(void)
{
    sceKernelExitGame();
    while (1) {}
}

