Mobile QA Multi-Agent Project

Welcome! This project is all about using a small team of AI helpers to test a mobile app automatically. You do not need to be a programmer to understand what this does. Here is the idea in plain language:

What it does:
This project creates a little but mighty “team” of computer help mates that can open a mobile app, follow some simple instructions, and then tell you if everything worked the way it should.

How it works in simple terms:
One helper decides what to do next, another helper does the tapping and swiping on the phone, and a third helper checks if the test passed or failed.

Why it’s useful:
It helps you test a mobile app without having to do everything by hand. Run the program, and it will do the testing for you.

And if the stars align:
If we’re lucky and the cosmos are on our side, we’ll be able to test multiple Android devices at the same time in the future. That’s the big goal at least!

I hope you find it easy to use and mhopefully it's not too glitchy.

# Mobile QA Agent – Decision Memo

I selected Simular's Agent S3 as the framework to support the Mobile QA Agent.

Simular Agent S3 is designed for multi-agent orchestration with clear roles:
- Planner: Determines next action
- Executor: Performs UI + ADB actions
- Supervisor: Validates success/failure

It supports structured workflows, branching logic, tool calling, and debugging observability, all essential for automated mobile QA testing.

It also scales well for:
Regression testing, multiple test suites, multiple devices, CI/CD integration

Google Agent Development Kit is powerful but lower-level. It lacks native multi-agent orchestration and would require significantly more engineering effort to replicate supervisory and planning intelligence that Simular already provides.

Simular Agent S3 is the most suitable agent framework due to:
Strong fit to assignment architecture, built-in planner/executor/supervisor model, robust orchestration, production-readiness

This framework best supports the CTO’s requirements and provides an ideal foundation for continued expansion of the QA automation platform.
