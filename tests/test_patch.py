from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PatchTests(unittest.TestCase):
    def test_production_parser_and_checked_region_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            subprocess.run(["git", "init", "-q", directory], check=True)
            subprocess.run(["git", "apply", "--include=src/intel/vulkan/anv_gpu_reclaim.h",
                            str(ROOT / "patches/0001-anv-experimental-gpu-reclaim.patch")], cwd=work, check=True)
            binary = work / "parser-tests"
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
                            "-I", str(work / "src/intel/vulkan"), str(ROOT / "tests/test_gpu_reclaim.c"),
                            "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_production_opt_in_helper_with_mocked_os_and_xe_queries(self):
        patch = (ROOT / "patches/0001-anv-experimental-gpu-reclaim.patch").read_text()
        start = patch.index("+/* Experimental Linux/Xe integrated-GPU path.")
        end = patch.index("\n static VkResult MUST_CHECK", start)
        helper = "\n".join(line[1:] for line in patch[start:end].splitlines() if line.startswith("+")) + "\n"
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            subprocess.run(["git", "init", "-q", directory], check=True)
            subprocess.run(["git", "apply", "--include=src/intel/vulkan/anv_gpu_reclaim.h",
                            str(ROOT / "patches/0001-anv-experimental-gpu-reclaim.patch")], cwd=work, check=True)
            (work / "anv_reclaim_integration.h").write_text(helper)
            binary = work / "integration-tests"
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
                            "-I", str(work / "src/intel/vulkan"), "-I", str(work),
                            str(ROOT / "tests/test_anv_integration.c"), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    unittest.main()
