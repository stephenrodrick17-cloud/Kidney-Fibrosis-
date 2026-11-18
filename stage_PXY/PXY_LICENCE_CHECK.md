# PXY licence check

Access date: 2026-11-18

No outside-model repository or weight is downloaded yet. No model run is performed.

## SarderLab/Multi-Compartment-Segmentation

- URL: https://github.com/SarderLab/Multi-Compartment-Segmentation
- Repository README: available publicly. Repository text says:
  "Multi compartment segmentation is a [detectron2](https://github.com/facebookresearch/detectron2) based panoptic segmentation model that is implemented as a pipeline in [Digital Slide Archive](https://athena.rc.ufl.edu/) (DSA) developed and maintained by [CMI lab](https://cmilab.nephrology.medicine.ufl.edu/) at the University of Florida."
- The README Quick Start requires:
  "Create an account at [DSA](https://athena.rc.ufl.edu/) and log in with your credentials."
  It then requires upload and selection of `Multi_compartment_model` from a DSA model collection.
- Repository licence file: NOT FOUND at the repository root or a standard `LICENSE` path checked on 2026-11-18.
- Verbatim licence text: NOT AVAILABLE. No licence or terms text can be quoted.
- Code research use: UNRESOLVED.
- Commercial or patent restriction: UNRESOLVED.
- Weight use: NOT AVAILABLE as a public repository weight. The README says a pre-trained model is available in a DSA collection, but the public repository does not provide the weight as a directly readable, licence-cleared file.
- Download/access conditions: account login and upload are required by the Quick Start. This conflicts with the required no-sign-up/no-access-request condition.
- Verdict: **BLOCKED**.
- Reason: no readable licence text, no public weight file, and account login/upload are required.

## vkola-lab/ajpa2021

- URL: https://github.com/vkola-lab/ajpa2021
- Branch checked: `master`.
- Repository licence: MIT License.
- Verbatim licence text:

  "MIT License

  Copyright (c) 2021 Kolachalama laboratory

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the \"Software\"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE."

- Code research use: ELIGIBLE under MIT, subject to the repository terms.
- Commercial or patent restriction: no commercial restriction is stated in the MIT licence text; no patent restriction is stated. MIT is not a patent license, and no patent use claim is made.
- README states:
  "We use WSIs obtained from The Ohio State University Wexner Medical Center (OSUWMC) and Kidney Precision Medicine Project (KPMP) respectively to evaluate the proposed model."
  It also says: "The OSUWMC dataset is not available for public use." It says KPMP WSIs can be downloaded from the KPMP website.
- Weight status: the public `models/` directory contains `resnet.py`, `resnet_fpn.py`, and `__init__.py`; no public checkpoint or weight file was found in that directory.
- Download of KPMP or other slide data is not authorized from the repository alone. The repository does not establish the licence or access terms for those WSIs.
- Verdict: **BLOCKED** for proxy execution. The code licence is readable and permits broad use, but the outside model weights are not actually provided and the README does not provide the KPMP slide licence needed for a direct download.

## Overall Step 1 result

- Outside proxy repositories eligible: **0**
- Downloaded outside weights or code: **0**
- Proxy comparison on KPMP: **NOT RUN**
- No download to `D:\patent\stage_PXY\data\`.

Because no candidate is ELIGIBLE, Step 3 is skipped. Step 2 may still run using PCT_PER_IMAGE.csv only.
