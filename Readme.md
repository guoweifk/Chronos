# Chronos: Timing-Oriented Testing Framework for Interaction Interference Failures in Cellular Core Networks

## Overview

This repository provides an anonymized artifact for **Chronos**, a timing-oriented testing framework for exposing
interaction interference failures in cellular core networks.

Chronos focuses on failures caused by unintended interference between concurrent control-plane procedures under
different execution timings.  
The framework operates in a black-box manner and uses only protocol-compliant UE behaviors.

The artifact is implemented using a lightweight **agent–server–center** architecture.

---

## Architecture

Chronos consists of three logical components:

- **control_center**  
  Global experiment controller and scheduler.

- **control_server**  
  Scenario coordinator that dispatches timing scenarios and UE behaviors.

- **agent**  
  Execution node that runs UE instances, applies timing perturbation, and reports observable results.

No modification to cellular core network implementations is required.

---

## Requirements

- Linux
- Docker / Docker Compose
- Python ≥ 3.8
- A running 4G or 5G cellular core network (not included)

---

## Quick Start

1. Configure the target deployment:

