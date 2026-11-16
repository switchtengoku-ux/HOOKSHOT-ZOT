/* (enhanced) Hookshot Enhanced: the product the Enhanced layer is built into (docs/enhanced/ARCHITECTURE.md).
   Every host/enh_* and gpu/vk/enh_* file takes the product's names from here, never as literals, so the same files can be
   carried to another fork of the same game (a Longshot Enhanced) by changing this file alone; tests/test_enh_product.py
   checks that no other Enhanced file names the product. scripts/enhanced/enh_product.py is its Python twin: keep both in
   step. Header only, C and C++, included by host/enh_*.c and gpu/vk/enh_photo.h. */
#ifndef ENH_PRODUCT_H
#define ENH_PRODUCT_H
#include <stdio.h>
#include <stdlib.h>

/* The game's name as players see it: the photos' folder (Pictures\<this>) and the photos' file names */
#define ENH_PRODUCT "Hookshot"
/* The fork's name, in the files the Enhanced layer writes */
#define ENH_ENHANCED ENH_PRODUCT " Enhanced"
/* The Insert menu's options file, beside the game (gpu/vk/vk_menu.cpp) */
#define ENH_OPTIONS "hookshot_options.ini"
/* The Enhanced switches' prefix, in the environment or the env file. It must be one the host's env file takes
   (host/hos_main.c: RX_, HOS_, HOOKSHOT_, ...): the product's own */
#define ENH_ENV_PREFIX "HOOKSHOT_ENH_"
/* The env file, for log lines */
#define ENH_ENV_FILE "hookshot_env.txt"
/* Where the Enhanced tools keep their files: %LOCALAPPDATA%\<ENH_STORE_WIN>\..., $XDG_DATA_HOME/<ENH_STORE_POSIX>/...,
   and the environment variables that move one store (<ENH_STORE_ENV_PREFIX>GRAPHICS, ...) */
#define ENH_STORE_WIN "HookshotZOT"
#define ENH_STORE_POSIX "hookshot-zot"
#define ENH_STORE_ENV_PREFIX "HOOKSHOT_ZOT_"

/* An Enhanced switch: enh_env("LIGHTBAR") reads HOOKSHOT_ENH_LIGHTBAR (NULL when unset) */
static inline const char *enh_env(const char *name) {
    char full[96];
    snprintf(full, sizeof full, "%s%s", ENH_ENV_PREFIX, name);
    return getenv(full);
}
/* A store's own variable: enh_store_env("GRAPHICS") reads HOOKSHOT_ZOT_GRAPHICS */
static inline const char *enh_store_env(const char *name) {
    char full[96];
    snprintf(full, sizeof full, "%s%s", ENH_STORE_ENV_PREFIX, name);
    return getenv(full);
}
#endif
