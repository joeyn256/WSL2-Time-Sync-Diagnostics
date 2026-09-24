# Python 3.12 vs Python 3.14 Under WSL2

This page covers the practical Python-version side of the Ubuntu 24.04 versus Ubuntu 26.04 decision.

The short version is simple:

> **Choose the interpreter your actual dependency set supports. Do not choose from version number alone.**

This project does not make a categorical claim that Python 3.14 is better than Python 3.12, or that Python 3.12 is the safer choice for every project.

## What we actually observed

In the accepted Ubuntu 26.04 default-state observation, the system Python was:

```text
Python 3.14.4
```

That tells us which interpreter was present in that environment.

It does **not** establish that an arbitrary Python project will install, build, or run correctly on 3.14.

The historical 24.04/26.04 work did not perform a comprehensive ecosystem-wide package survey.

## The compatibility question that matters

For a real project, check your own dependencies.

Do not assume that the same dependency artifacts are available for Python 3.12 and Python 3.14. Check:

- your project's `Requires-Python` constraints;
- compatible wheel availability;
- native-extension support;
- whether a dependency falls back to a source build;
- compiler/system-library requirements;
- whether the package's own tests or your application tests pass.

This matters most for packages with compiled components, platform-specific bindings, or slower release cycles.

## A practical decision process

### Start with your application

List the packages you actually need.

For example:

```text
numpy
pandas
scipy
duckdb
pyarrow
requests
your-own-package
```

The exact list matters more than broad claims about "Python compatibility."

### Test in a clean environment

For each interpreter you are considering:

1. create a clean virtual environment;
2. install the project from the same dependency definition;
3. record which packages install from wheels versus source;
4. run the project's actual test suite;
5. run a representative workload;
6. record exact versions.

A successful `pip install` is useful, but it is not the same thing as application compatibility.

## When Python 3.14 makes sense

Python 3.14 is a reasonable choice when:

- your direct and transitive dependencies support it;
- the packages you rely on provide suitable artifacts for your platform;
- your tests pass;
- you are starting a new project and do not need older interpreter compatibility.

The Ubuntu 26.04 environment observed in this project already included Python 3.14.4, which makes it a natural interpreter to evaluate there.

That is an environment fact, not a recommendation for every workload.

## When Python 3.12 can be the better engineering choice

Python 3.12 can be the lower-risk choice when:

- your dependency stack is already proven on it;
- one or more important packages are not yet proven on 3.14 in your environment;
- you depend on compiled/native extensions with version-specific artifacts;
- you need compatibility with another deployment environment pinned to 3.12;
- changing interpreters would add migration work without a clear benefit.

Using an older supported interpreter is not automatically "falling behind." Stability and dependency compatibility are valid engineering requirements.

## Wheels versus source builds

One subtle difference between interpreter versions can be artifact availability.

A package may install as a prebuilt wheel on one interpreter and require a source build on another.

That changes the practical risk because source builds can depend on:

- compilers;
- development headers;
- system libraries;
- build backends;
- architecture-specific configuration.

When comparing interpreters, record whether the install used a wheel or built from source.

Do not generalize one package's behavior to the entire Python ecosystem.

## Avoid replacing the system Python

For project testing, prefer a virtual environment or another isolated interpreter setup.

Do not replace Ubuntu's system Python just to evaluate compatibility.

A clean project environment makes the result easier to reproduce and reduces the chance of breaking distro-managed tooling.

## Timing and Python version are separate questions

This project's WSL2 timing observations and its Python-version decision are related only because they affect the same environment choice.

They are different claims:

- a clean timing observation does not prove package compatibility;
- successful package installation does not prove stable WSL2 timing;
- Python 3.14 being present on Ubuntu 26.04 does not explain the timing result.

Treat the two decisions separately, then combine them when choosing an environment.

## Suggested compatibility record

For each tested environment, record:

```text
date
Windows version
WSL version
Ubuntu version
architecture
Python version
package source/index
package versions
wheel vs source build
installation result
test result
representative workload result
```

That makes future conclusions dated and reproducible rather than timeless.

## Bottom line

Use Python 3.14 when your actual project supports it and the newer environment is useful to you.

Use Python 3.12 when compatibility or deployment constraints make it the safer choice.

The best answer comes from testing **your dependency set**, not from ranking interpreter version numbers.
