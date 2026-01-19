🧪 LabMate: Laboratory & Project Management System

📖 Overview

LabMate is a comprehensive, Python-based desktop application designed to streamline scientific research workflows and laboratory management. It serves as a unified platform for tracking projects, maintaining electronic lab notebooks (ELN), managing Standard Operating Procedures (SOPs), and securing data through hybrid backup solutions.

This project is developed with the philosophy of Free and Open Source Software (FOSS). We believe that scientific tools should be accessible, transparent, and modifiable by the community.

✨ Key Features

🗂 Project Management: Create, track, and manage multiple research projects with assigned researchers and timelines.

📝 Electronic Lab Notebook (ELN): Record daily experiments with timestamped entries. Supports multi-user selection for collaborative experiments.

📋 SOP Management: Create detailed Standard Operating Procedures with dynamic material lists and step-by-step instructions. includes version tracking.

☁️ Hybrid Backup System:

Local Backup: Automatically mirrors data to a specified local directory (USB, OneDrive folder, etc.).

Cloud Integration: Native support for Google Drive API to securely upload encrypted backup files.

📎 File Management: Attach and reference external files (PDFs, Images, Data Logs) directly within specific projects.

🛡️ Data Safety: "Safe Delete" protocols ensure data is backed up before any permanent deletion occurs.

🚀 Installation & Usage

Prerequisites

Python 3.x

Google Cloud Console credentials (optional, for Drive API features)

Steps

Clone the repository:

git clone [https://github.com/yourusername/LabMate.git](https://github.com/yourusername/LabMate.git)
cd LabMate


Install required dependencies:

pip install google-api-python-client google-auth-oauthlib google-auth-httplib2


(Optional) For Google Drive integration, place your credentials.json file in the root directory.

Run the application:

python LabMate_Final.py


🤝 Contributing & Freedom to Modify

LabMate is Free Software.

This means you are free to use, study, share, and modify the software. We strongly encourage students, researchers, and developers to fork this repository and customize it to fit their specific laboratory needs.

Whether you want to add a chemical inventory module, integrate with other APIs, or simply improve the UI—your contributions are welcome!

How to Contribute

Fork the Project.

Create your Feature Branch (git checkout -b feature/AmazingFeature).

Commit your Changes (git commit -m 'Add some AmazingFeature').

Push to the Branch (git push origin feature/AmazingFeature).

Open a Pull Request.

🚧 Development Status

Current Version: v0.1 (Alpha)

Please note that LabMate is currently under active development. While the core features are functional, you may encounter bugs or incomplete features. We are working regularly to improve stability and add new functionalities.

👤 Author

Bertan Yurteri

Contact: bertanyurteri1069@gmail.com

Disclaimer: This software is provided "as is", without warranty of any kind.
