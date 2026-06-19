# MedKGent

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20759287.svg)](https://doi.org/10.5281/zenodo.20759287)

Welcome to the MedKGent repository! This repository contains the code for MedKGent, a framework designed for constructing temporally evolving medical knowledge graphs using large language models.

![MedKGent Overview](figs/Figure1.jpg)

## 📧 Contact

For any questions, suggestions, or collaboration opportunities, please feel free to reach:

| Contact | Email |
|:---:|:---:|
| **Duzhen Zhang** | 📧 [duzhen.zhang@mbzuai.ac.ae](mailto:duzhen.zhang@mbzuai.ac.ae) |

## 📰 News

- **[2026.06.18]** We open-sourced the **MedKGent** codebase.

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/BladeDancer957/MedKGent.git
cd MedKGent
```

### 2. Create the conda environment

```bash
conda env create -f environment.yaml
conda activate medkgent
```

Alternatively, if you prefer using pip directly:

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root directory. The file should define the following variables:

| Variable | Description |
|:---|:---|
| `API_KEY` | API key for the commercial LLM service. |
| `BASE_URL` | LLM API base URL, for example the DashScope compatible endpoint. |
| `NEO4J_URI` | Neo4j connection URI, for example a local Bolt URI. |
| `NEO4J_USER` | Neo4j username. |
| `NEO4J_PASSWORD` | Neo4j password. |
| `NEO4J_DATABASE` | Neo4j database name. |

Please do not commit your real `.env` file to GitHub.

### 4. Run MedKGent

Make sure `run.sh` is executable:

```bash
chmod +x run.sh
```

Then run:

```bash
./run.sh
```

You can also override the default runtime parameters:

```bash
./run.sh --model qwen-max --base_dir ./data_samples --N 50 --confidence_threshold 0.6
```

## 🧠 MedKGent-KG

You can explore the Medical Knowledge Graph built using the MedKGent framework here: [MedKGent-KG](https://huggingface.co/datasets/ShowerMaker/MedKGent-KG).

## ⚙️ Notes

The current code version in this repository uses ready-to-use commercial LLM APIs and processes abstracts serially in chronological order.

Since the number of abstracts to be processed is very large, at the scale of tens of millions, we deployed open-source LLMs ourselves when using MedKGent to reduce API calling costs, and we also implemented parallel extraction to accelerate.

If you have any questions or need help with deploying open-source LLMs or accelerating extraction with parallel processing, please feel free to contact us.

## Citations

If you use this framework or dataset in your research, please cite the following paper:

```bibtex
@article{zhang2025medkgent,
  title={MedKGent: A Large Language Model Agent Framework for Constructing Temporally Evolving Medical Knowledge Graph},
  author={Zhang, Duzhen and Wang, Zixiao and Li, Zhong-Zhi and Yu, Yahan and Jia, Shuncheng and Dong, Jiahua and Xu, Haotian and Wu, Xing and Zhang, Yingying and Zhang, Tielin and others},
  journal={arXiv preprint arXiv:2508.12393},
  year={2025}
}
```