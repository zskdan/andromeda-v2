# Andromeda WB Video Link — System Architect Input

## 1. Mission Context

Andromeda is an experimental rocket / technology demonstrator.

Relevant WB communications objective:

- Real-time transmission of onboard video to the ground.
- Maximum expected slant range: approximately **10 km**.
- Vehicle velocity may approach approximately **Mach 1**.
- Initial RF development platform: **one PlutoSDR**.
- Target implementation should ultimately be suitable for FPGA acceleration / implementation.
- Narrow-band telemetry/control is a separate waveform and is outside the scope of this WB PHY task.

---

## 2. Video Requirement

Initial target video stream:

- Resolution: **4K UHD, 3840 × 2160**
- Frame rate: **60 fps**
- Codec: **H.265 / HEVC**
- Expected compressed bitrate: approximately **30–40 Mbps**
- Design target for WB PHY usable payload throughput: approximately **50 Mbps**

The PHY should provide sufficient margin for:

- video packetization,
- framing,
- FEC,
- pilots,
- synchronization,
- cyclic prefix,
- guard carriers,
- possible transport overhead.

---

## 3. Baseline WB PHY Requirement

Use the following as the initial reference waveform:

- Waveform: **CP-OFDM**
- RF occupied bandwidth: approximately **15 MHz**
- Nominal modulation: **64-QAM**
- FEC coding rate: **3/4**
- Target usable payload throughput: approximately **50 Mbps**
- Nominal subcarrier spacing: approximately **30–60 kHz**
- Initial design point: around **30 kHz**, subject to simulation and Pluto implementation constraints.

The implementation should support selectable modulation modes:

- QPSK
- 16-QAM
- 64-QAM

64-QAM is the nominal Andromeda WB mode.

QPSK exists primarily as:

- synchronization/debug mode,
- low-SNR fallback,
- degraded-link operating mode.

256-QAM may be implemented later as an optional high-SNR mode but **must not be required for mission success**.

---

## 4. Approximate PHY Efficiency Budget

Starting assumptions:

- Edge guard subcarriers: approximately **8–10%**
- Pilot overhead: approximately **6–8%**
- Cyclic-prefix overhead: approximately **6%**
- Preamble/framing overhead: approximately **1–3%**
- FEC: rate **3/4**

Expected overall result for:

**15 MHz + 64-QAM + 3/4 FEC**

is approximately:

**~50 Mbps usable payload throughput**

The architect must calculate the exact throughput from the selected FFT size, active carriers, CP, pilot pattern, frame structure and coding.

---

## 5. Doppler Requirement

The rocket may travel close to Mach 1.

At approximately 2.4 GHz, maximum radial Doppler around Mach 1 is approximately:

**±2.7 kHz**

The PHY shall tolerate this dynamic Doppler with margin.

Do not treat spectral guard bands as the primary Doppler solution.

Use:

- preamble-based coarse carrier frequency offset estimation,
- pilot-based continuous carrier/phase tracking,
- sufficiently large OFDM subcarrier spacing,
- residual CFO correction.

The acquisition range should also tolerate Pluto / RF oscillator frequency error, which may be substantially larger than the actual rocket Doppler.

Initial receiver design should target a carrier-frequency acquisition range on the order of:

**±50–100 kHz**

followed by fine CFO/Doppler tracking.

---

## 6. Multipath and Channel Robustness

Use a cyclic prefix.

Initial candidate:

- subcarrier spacing: ~30 kHz
- useful OFDM symbol duration: ~33.3 µs
- CP approximately 1/16
- CP duration: approximately **2.1 µs**

The exact CP shall be validated against expected ground-reflection / multipath scenarios.

Frequency-selective fading should be handled using:

- pilot-assisted channel estimation,
- per-subcarrier equalization,
- FEC,
- interleaving.

---

## 7. Rotation / Antenna Fading

Rocket rotation and polarization/orientation fading are **not solved by additional OFDM guard intervals**.

These impairments should be addressed at system level using:

- appropriate antenna polarization,
- multiple antennas / spatial coverage around the rocket,
- receiver diversity where possible,
- FEC,
- interleaving,
- robust fallback modulation,
- potentially adaptive modulation later.

The waveform should therefore expose channel-quality metrics that can eventually support link adaptation.

Examples:

- RSSI
- SNR estimate
- EVM
- BER/PER
- channel estimate quality
- CFO/Doppler estimate

---

## 8. PAPR Constraint

CP-OFDM has relatively high Peak-to-Average Power Ratio.

This affects:

- PA efficiency,
- required PA back-off,
- achievable RF output power,
- battery consumption,
- distortion/EVM.

The implementation and RF testing must measure:

- PAPR,
- EVM versus PA back-off,
- BER/PER versus PA operating point.

Do not optimize purely for digital-link throughput while ignoring the RF PA.

---

## 9. Plan B Waveform

If CP-OFDM PA efficiency becomes a significant system limitation, evaluate:

**DFT-s-OFDM / SC-FDMA + 64-QAM**

as the primary Plan B.

Reasons:

- similar high spectral efficiency,
- OFDM-style frequency-domain equalization,
- typically lower PAPR than conventional OFDM,
- potentially better fit for an airborne power-constrained transmitter.

Compare CP-OFDM and DFT-s-OFDM using identical or comparable:

- bandwidth,
- modulation,
- FEC,
- throughput,
- RF hardware.

Comparison metrics:

- BER/PER versus SNR,
- required Eb/N0,
- EVM,
- PAPR,
- PA back-off,
- actual RF output power,
- implementation complexity,
- FPGA resource usage,
- latency.

Do not switch to DFT-s-OFDM without measured evidence that its RF/system advantage justifies the additional complexity.

---

## 10. Initial Development Platform

Currently only **one PlutoSDR** is available.

Initial development shall therefore support a one-Pluto test setup.

Recommended progression:

### Phase 1 — Pure software reference model

Build a bit-exact reference waveform in Python.

TX chain:

```text
Data
→ framing
→ FEC
→ interleaving
→ QAM mapper
→ pilot insertion
→ OFDM resource mapping
→ IFFT
→ cyclic prefix
→ preamble/frame construction
```

RX chain:

```text
sample synchronization
→ frame detection
→ coarse CFO correction
→ CP removal
→ FFT
→ pilot extraction
→ channel estimation
→ equalization
→ fine phase/CFO tracking
→ QAM demapping
→ deinterleaving
→ FEC decoding
→ frame checking / BER/PER
```

---

### Phase 2 — Channel simulation

Implement impairments independently and in combination:

- AWGN
- static CFO
- dynamic Doppler
- multipath
- frequency-selective fading
- phase noise approximation
- IQ imbalance
- clipping / PA nonlinearity
- packet/frame loss

Specifically test:

- Doppler from 0 to at least ±3 kHz
- oscillator offset significantly larger than Doppler
- time-varying channel conditions.

---

### Phase 3 — Single Pluto loopback

Use one PlutoSDR in TX/RX loopback.

Preferred initial setup:

```text
TX RF
→ suitable attenuation
→ RX RF
```

Avoid direct TX-to-RX connection without the required attenuation/protection.

Validate:

- synchronization,
- CFO estimation,
- channel estimation,
- BER,
- PER,
- EVM,
- achievable sustained throughput.

---

### Phase 4 — 64-QAM target validation

QPSK may be used first to verify basic synchronization.

Move immediately to the nominal mode:

**15 MHz / 64-QAM / FEC 3/4**

Primary validation shall be performed using 64-QAM.

---

### Phase 5 — Video integration

Replace synthetic payload with H.265 video.

Measure:

- sustainable application throughput,
- latency,
- packet loss,
- decoder behavior under packet loss,
- recovery after temporary fades.

Do not couple video debugging with PHY debugging too early.

Synthetic deterministic payloads must remain available for PHY validation.

---

### Phase 6 — FPGA migration

Once the software/reference implementation is stable, progressively migrate deterministic high-rate PHY functions into FPGA.

Candidate FPGA functions:

- QAM mapper/demapper
- pilot/resource mapper
- IFFT/FFT
- cyclic-prefix insertion/removal
- correlators/preamble detection
- channel estimation
- equalization
- possibly FEC depending selected code and resource budget

The software reference model must remain the golden model for RTL verification.

---

## 11. Pluto Architectural Constraint

Evaluate two possible architectures:

### Architecture A — Pluto contains the PHY

Pluto Zynq PL implements most of the OFDM modem and AD936x acts as RF frontend.

Advantages:

- avoids transporting high-rate raw I/Q externally,
- deterministic PHY,
- lower host-interface bandwidth,
- closer to a deployable radio.

This is the preferred long-term Pluto architecture if feasible.

### Architecture B — External processor/FPGA performs PHY

Kria or another main Andromeda compute platform generates/receives I/Q and Pluto acts mainly as RF frontend.

Useful for prototyping, but external Pluto interface bandwidth and latency may become limiting.

Avoid making raw sample transfer over USB a fundamental dependency of the final architecture.

---

## 12. Required Modem Observability

The implementation must expose sufficient internal metrics for engineering validation.

At minimum:

- TX frame counter
- RX frame counter
- lost-frame counter
- CRC errors
- BER where known payload permits it
- packet error rate
- EVM
- RSSI
- estimated SNR
- coarse CFO
- fine/residual CFO
- estimated Doppler
- timing offset
- channel estimates
- FEC correction statistics

These values should be easily logged during experiments.

---

## 13. Design Philosophy

Priorities, in order:

1. **Reliable 4K60 H.265 transport**
2. Robustness over the expected rocket channel
3. Practical RF power efficiency
4. Deterministic FPGA implementation
5. Spectral efficiency
6. Optional peak-throughput modes

Do not select 256-QAM simply to maximize theoretical throughput.

Prefer:

**15 MHz + robust 64-QAM**

over:

**10 MHz + fragile 256-QAM**

unless actual link-budget and RF measurements demonstrate that 256-QAM provides a useful operational benefit.

---

## 14. Initial Deliverable Requested from System Architect

Produce a concrete WB PHY architecture proposal containing:

1. exact OFDM numerology:
   - sample rate
   - FFT size
   - subcarrier spacing
   - number of active carriers
   - guard carriers
   - DC carrier policy
   - CP length

2. exact frame structure:
   - preamble
   - synchronization sequences
   - pilot placement
   - data symbols
   - frame duration

3. exact FEC recommendation:
   - code family
   - block size
   - coding rate
   - interleaver

4. exact achievable payload-rate calculation

5. Doppler/CFO acquisition and tracking algorithm

6. channel-estimation/equalization approach

7. PlutoSDR implementation architecture

8. Python reference-model structure

9. FPGA partitioning strategy

10. verification plan and measurable acceptance criteria

11. CP-OFDM versus DFT-s-OFDM trade study

12. list of unresolved requirements or assumptions that must be validated before freezing the PHY.

The architect should challenge any numerical assumption where appropriate rather than treating the current values as frozen requirements.
