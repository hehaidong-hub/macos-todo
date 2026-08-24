/* launcher.c — 启动 Todo (Python/Tk) App
 *
 * Tk 8.5 在 Apple Silicon 上画 Retina 窗口有已知 bug（窗口全白/空白），
 * 所以优先用 brew Python 3.9（带 Tk 8.6），退回 brew python3，最后才用 env python3。
 *
 * 路径解析：
 *   launcher = .../Todo.app/Contents/MacOS/launcher
 *   切 4 段 → .../Todo  ← todo_app.py 在这里
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/param.h>
#include <unistd.h>

static int try_exec(char *const argv[], const char *label) {
    execv(argv[0], argv);
    fprintf(stderr, "launcher: %s 不可用 (%s)\n", label, argv[0]);
    return -1;
}

int main(int argc, char **argv) {
    char app_dir[PATH_MAX];
    char script_path[PATH_MAX];
    char *p;
    int cuts;
    (void)argc;

    if (!realpath(argv[0], app_dir)) {
        fprintf(stderr, "launcher: realpath(%s) failed\n", argv[0]);
        return 1;
    }
    p = app_dir + strlen(app_dir);
    cuts = 0;
    while (p > app_dir && cuts < 4) {
        p--;
        if (*p == '/') cuts++;
    }
    if (cuts < 4) {
        fprintf(stderr, "launcher: cannot resolve bundle path from %s\n", app_dir);
        return 1;
    }
    *p = '\0';
    snprintf(script_path, sizeof(script_path), "%s/todo_app.py", app_dir);

    char *const brew_39[] = {
        "/opt/homebrew/bin/python3.9", script_path, NULL,
    };
    char *const brew_3[] = {
        "/opt/homebrew/bin/python3", script_path, NULL,
    };
    char *const env_py3[] = {
        "/usr/bin/env", "env", "python3", script_path, NULL,
    };

    if (try_exec(brew_39, "brew python3.9") == 0) return 0;
    if (try_exec(brew_3,   "brew python3")   == 0) return 0;
    if (try_exec(env_py3,  "env python3")    == 0) return 0;

    fprintf(stderr, "launcher: no working python3 found\n");
    return 1;
}
