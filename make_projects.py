"""Generate synthetic pytest/cargo/jest projects with realistic pass+fail output."""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")

# ------------------------------ pytest project ------------------------------
PY = os.path.join(ROOT, "pyproj")
os.makedirs(os.path.join(PY, "tests"), exist_ok=True)

utils_py = '''"""Benchmark helpers for the rtk pytest scenario."""


def add(a, b):
    """Return the sum of a and b."""
    return a + b


def divide(a, b):
    """Return a divided by b."""
    return a / b


def lookup(table, key):
    """Return table[key]."""
    return table[key]


def transform(items, factor=2):
    """Return items scaled by factor."""
    return [i * factor for i in items]


def legacy_helper(value):
    """Deprecated helper kept for compatibility."""
    import warnings

    warnings.warn(
        "legacy_helper is deprecated; use transform()",
        DeprecationWarning,
        stacklevel=2,
    )
    return value * 2
'''
with open(os.path.join(PY, "utils.py"), "w") as f:
    f.write(utils_py)

lines = [
    '"""Passing arithmetic tests (generated for the rtk benchmark)."""',
    "import utils",
    "",
]
for i in range(100):
    a, b = i, i * 3 + 1
    lines += [
        f"def test_add_{i:03d}():",
        f'    """Verify add({a}, {b})."""',
        f"    assert utils.add({a}, {b}) == {a + b}",
        f"    assert utils.transform([{a}]) == [{a * 2}]",
        "",
    ]
lines += [
    "def test_legacy_compatibility():",
    '    """Legacy path still works (emits a DeprecationWarning)."""',
    "    assert utils.legacy_helper(21) == 42",
    "",
    "def test_legacy_compatibility_again():",
    '    """Legacy path, second call site (emits another DeprecationWarning)."""',
    "    assert utils.legacy_helper(5) == 10",
    "",
]
with open(os.path.join(PY, "tests", "test_math.py"), "w") as f:
    f.write("\n".join(lines))

api_py = '''"""Failing API tests (generated for the rtk benchmark)."""
import pytest

import utils


def test_divide_by_zero():
    assert utils.divide(10, 0) == float("inf")


def test_lookup_missing_key():
    table = {"alpha": 1, "beta": 2}
    assert utils.lookup(table, "omega") == 0


def test_add_wrong_expectation():
    assert utils.add(2, 3) == 6


def test_transform_wrong_factor():
    assert utils.transform([1, 2, 3], factor=2) == [1, 2, 3]


@pytest.mark.parametrize("a,b,expected", [(1, 1, 3), (2, 2, 5), (4, 4, 9)])
def test_add_parametrized(a, b, expected):
    assert utils.add(a, b) == expected


def test_type_error():
    assert utils.add("1", 1) == 2


def test_deep_stack_failure():
    """Nested helpers so the traceback spans several frames."""

    def level3():
        assert utils.divide(1, 0) == 0

    def level2():
        level3()

    def level1():
        level2()

    level1()
'''
with open(os.path.join(PY, "tests", "test_api.py"), "w") as f:
    f.write(api_py)

edge_py = '''"""Failing edge-case tests (generated for the rtk benchmark)."""


def test_string_case():
    name = "rtk"
    assert name.upper() == "rtk"


def test_list_slice():
    data = list(range(10))
    assert data[3:6] == [3, 4, 5, 6]


def test_dict_key_missing():
    cfg = {"host": "localhost", "port": 8080}
    assert cfg["user"] == "admin"
'''
with open(os.path.join(PY, "tests", "test_edge.py"), "w") as f:
    f.write(edge_py)

# ------------------------------ cargo project ------------------------------
RS = os.path.join(ROOT, "rsproj")
os.makedirs(os.path.join(RS, "src"), exist_ok=True)
with open(os.path.join(RS, "Cargo.toml"), "w") as f:
    f.write(
        "[package]\n"
        'name = "rtkbench"\n'
        'version = "0.1.0"\n'
        'edition = "2021"\n\n'
        "[lib]\n"
        'path = "src/lib.rs"\n'
    )

lib_lines = [
    "//! rtk benchmark crate: helpers plus a deliberately failing test suite.",
    "",
    "/// Adds two integers.",
    "pub fn add(a: i32, b: i32) -> i32 {",
    "    a + b",
    "}",
    "",
    "/// Divides `a` by `b`.",
    "pub fn divide(a: i32, b: i32) -> i32 {",
    "    a / b",
    "}",
    "",
    "/// Scales a slice by `factor`.",
    "pub fn scale(items: &[i32], factor: i32) -> Vec<i32> {",
    "    items.iter().map(|i| i * factor).collect()",
    "}",
    "",
    "#[cfg(test)]",
    "mod tests {",
    "    use super::*;",
    "",
]
for i in range(40):
    a, b = i + 1, i * 2 + 5
    lib_lines += [
        f"    #[test]",
        f"    fn add_works_{i:03d}() {{",
        f"        assert_eq!(add({a}, {b}), {a + b});",
        f"        assert_eq!(scale(&[{a}], 2), vec![{a * 2}]);",
        "    }",
        "",
    ]
lib_lines += [
    "    #[test]",
    "    fn add_fails_000() {",
    "        assert_eq!(add(2, 3), 6);",
    "    }",
    "",
    "    #[test]",
    "    fn add_fails_001() {",
    "        assert_eq!(add(10, 20), 35);",
    "    }",
    "",
    "    #[test]",
    "    fn scale_fails_000() {",
    '        assert_eq!(scale(&[1, 2, 3], 2), vec![1, 2, 3]);',
    "    }",
    "",
    "    #[test]",
    "    fn divide_by_zero_fails() {",
    "        assert_eq!(divide(10, 0), 0);",
    "    }",
    "",
    "    #[test]",
    "    fn missing_feature_fails() {",
    '        panic!("feature not implemented yet: retry with backoff");',
    "    }",
    "",
    "    #[test]",
    "    fn invariant_fails() {",
    '        assert!(add(1, 1) == 3, "invariant violated: expected 3");',
    "    }",
    "}",
]
with open(os.path.join(RS, "src", "lib.rs"), "w") as f:
    f.write("\n".join(lib_lines))

# ------------------------------ jest project ------------------------------
JS = os.path.join(ROOT, "jsproj")
os.makedirs(os.path.join(JS, "tests"), exist_ok=True)
with open(os.path.join(JS, "package.json"), "w") as f:
    json.dump(
        {
            "name": "rtkbench-js",
            "version": "1.0.0",
            "private": True,
            "scripts": {"test": "jest"},
            "devDependencies": {"jest": "^29.7.0"},
        },
        f,
        indent=2,
    )

math_js = ["// Passing arithmetic tests (generated for the rtk benchmark).", ""]
for i in range(30):
    a, b = i, i + 7
    math_js += [
        f"test('add {i:02d}', () => {{",
        f"  expect({a} + {b}).toBe({a + b});",
        f"  expect([{a}].map((x) => x * 2)).toEqual([{a * 2}]);",
        "});",
        "",
    ]
with open(os.path.join(JS, "tests", "math.test.js"), "w") as f:
    f.write("\n".join(math_js))

api_js = """// Failing API tests (generated for the rtk benchmark).
const { add, divide, lookup } = require('../src/api');

test('divide by zero returns Infinity', () => {
  expect(divide(10, 0)).toBe(Infinity);
});

test('lookup missing key returns 0', () => {
  expect(lookup({ alpha: 1 }, 'omega')).toBe(0);
});

test('add 2 + 3 equals 6', () => {
  expect(add(2, 3)).toBe(6);
});

test('network retry recovers', () => {
  throw new Error('connection refused: retry budget exhausted');
});
"""
os.makedirs(os.path.join(JS, "src"), exist_ok=True)
with open(os.path.join(JS, "tests", "api.test.js"), "w") as f:
    f.write(api_js)
with open(os.path.join(JS, "src", "api.js"), "w") as f:
    f.write(
        "function add(a, b) {\n  return a + b;\n}\n\n"
        "function divide(a, b) {\n  return a / b;\n}\n\n"
        "function lookup(table, key) {\n  return table[key];\n}\n\n"
        "module.exports = { add, divide, lookup };\n"
    )

str_js = """// Failing string tests (generated for the rtk benchmark).
test('uppercase conversion', () => {
  expect('rtk'.toUpperCase()).toBe('rtk');
});

test('string slice', () => {
  expect('benchmark'.slice(0, 4)).toBe('benchmar');
});
"""
with open(os.path.join(JS, "tests", "string.test.js"), "w") as f:
    f.write(str_js)

print("projects generated at", ROOT)
for p in ("pyproj", "rsproj", "jsproj"):
    n = sum(len(fs) for _, _, fs in os.walk(os.path.join(ROOT, p)))
    print(f"  {p}: {n} files")
