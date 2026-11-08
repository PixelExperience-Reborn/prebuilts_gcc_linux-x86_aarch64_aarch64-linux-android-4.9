# Android 17 / mondrian — historical AArch64 GCC 4.9 boundary

**2026-11-08. Step 189 / 135 repository audit. Target: POCO F5 Pro / Redmi K60 (mondrian).**

**Decision:** preserve the original PE AArch64 GNU GCC 4.9 prebuilt, but exclude it from all active Android 17 platform profiles. Do not automatically select it as the compiler or assembler for Linux 5.10. A separate kernel toolchain assessment is required.

## Original PixelExperience repository and intent

- GitHub repo: https://github.com/PixelExperience-Reborn/prebuilts_gcc_linux-x86_aarch64_aarch64-linux-android-4.9
- Source branch: seventeen; original HEAD a0c13e0de2201201342fd5c87d77f25105e5c42e (2021-12-11). Original Git tree e7490667e01ac0301c96915927902e3e654437d0.
- Original bin tree: b7f6196a9a7b53c4785178d6c4a6cd33ffcf044f. It contains the historical GCC 4.9 wrapper / compiler, GNU assembler, ld.bfd/ld.gold, objcopy, strip, nm and other binutils. These archived objects are not replaced.
- Last historical commit introduced minimal aarch64-linux-gnu- compatibility aliases for older LLVM builds with GNU external tools. The commit mentions an external assembler for LLVM_IAS=0.
- The archive is **not a complete reliable modern GNU prefix**: bin/aarch64-linux-gnu-as is a symlink, while bin/aarch64-linux-gnu-elfedit is a ZERO-BYTE executable (Git blob e69de29bb2d1d6434b8b29ae775ad8c2e48c5391, mode 100755). Its name alone is no proof of functional elfedit support.
- Original repo.prop records toolchain/gcc, binutils and GNU build-component provenance. It is not an Android17 regeneration recipe.
- Original PE manifest/seventeen includes the GCC49 checkout in snippets/pixel-extras.xml. Preserve that history without migrating old Android14 product toolchains into the new base.

## Official AOSP17 source graph

- Independent PE-Reborn baseline: Google AOSP android-17.0.0_r1, not LineageOS or CLO.
- Official AOSP17 manifest has the canonical platform/prebuilts/clang/host/linux-x86 project; it does not contain this old AArch64 GCC49 project.
- The reviewed PE build_soong commit 6215d41c790a463b7795ce81ac77204c238cbf48 pins the platform ClangDefaultVersion to clang-r584948 in cc/config/global.go. This says NOTHING about the correct Clang for the device Linux 5.10 kernel.
- Official AOSP17 also has unrelated HOST GCC 4.8 prebuilts. Those are distinct projects and must not be forbidden under a broad GCC blacklist.
- The manifest validator must prevent AArch64 GCC49 import under its historical checkout path or repository alias, including a renamed checkout, across staged and candidate graphs. Leave the historical source branch and the independent AOSP17 default.xml intact.

## How to choose a mondrian kernel toolchain

Official kernel LLVM build guidance: https://docs.kernel.org/kbuild/llvm.html

The Linux kernel can use LLVM=1 with integrated assembler; if LLVM_IAS=0 is necessary it needs a compatible CROSS_COMPILE assembler prefix. Whether the existing Xiaomi SM8475 kernel 5.10 requires that fallback has **not** been established. Do not automatically turn on LLVM_IAS=0 or use these 2021 GCC49 tools.

Before choosing a pinned toolchain, inspect the actual kernel Makefile/defconfig, scripts, LLVM/LLD/IAS options, CROSS_COMPILE and CROSS_COMPILE_COMPAT, module / DTBO build rules, LTO/CFI configuration and assembler corner cases. If external GNU tools are proven necessary, select and validate a complete, supported prefix separately.

Real exit gates: compile kernel Image, dtbs/dtbo, modules; check warnings and ELF/module symbols/vermagic, supported KMI / vendor ABI, vendor boot layout, AVB/VINTF/FCM, boot, stability and game/performance behavior on a physical POCO F5 Pro / Redmi K60. An old kernel toolchain is not validated by checking the manifest.

## Checks in this audit PR

- A Python3 source-only suite checks Git ancestry, original tree object IDs and specific GNU binary/symlink modes without executing historic binaries.
- It validates that official AOSP17 reference uses the correct host Clang, that old GCC49 is absent from that source graph, and that pinned Soong uses the modern platform Clang.
- GitHub Actions uses sparse blob-filtered checkout, validates current PE-Reborn 135-row manifest and source profiles, and runs the standalone GCC archive regression test.

**Not performed:** full source sync, Soong bootstrap, compilation of AOSP17, build/boot of kernel Linux 5.10, compatibility with kernel modules, OTA, or tests on physical mondrian. A PASS means only source/metadata policy and integrity checks passed.
