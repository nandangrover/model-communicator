## Model Communicator System
This system comprises of two subsytems:

#### Data Curation and Quantization
The notebook contains the code for curating the data for fine-tuning. For fine-tuning we follow the steps in Step 3. The notebook also contains the code for the quantization of the fine-tuned models.

#### Fine-tuning using Alpaca Lora

##### Step 1: Clone the Alpaca-LoRA repo

We’ve created a fork of the original Alpaca-LoRA repo that adds support for Cog. Cog is a tool to package machine learning models in containers and we're using it to install the dependencies to fine-tune and run the model.

Clone the repository using Git:

```
git clone https://github.com/daanelson/alpaca-lora
cd alpaca-lora
```

##### Step 2: Get LLaMA weights
Put your downloaded LLaMA weights in a folder called unconverted-weights. The folder hierarchy should look something like this:
```
unconverted-weights
├── 7B
│   ├── checklist.chk
│   ├── consolidated.00.pth
│   └── params.json
├── tokenizer.model
└── tokenizer_checklist.chk
```
Convert the weights from a PyTorch checkpoint to a transformers-compatible format using this command:

```
cog run python -m transformers.models.llama.convert_llama_weights_to_hf \
  --input_dir unconverted-weights \
  --model_size 7B \
  --output_dir weights
```
You final directory structure should look like this:

```
weights
├── llama-7b
└── tokenizermdki
```

##### Step 3: Install Cog
```
sudo curl -o /usr/local/bin/cog -L "https://github.com/replicate/cog/releases/latest/download/cog_$(uname -s)_$(uname -m)"
sudo chmod +x /usr/local/bin/cog
```

##### Step 4: Fine-tune the model
The fine-tuning script is configured by default to work on less powerful GPUs, but if you have a GPU with more memory, you can increase MICRO_BATCH_SIZE to 32 or 64 in finetune.py .

We need to place our curated dataset generated using **Data_Curation_and_Quantization.ipynb** in the root directory and edit DATA_PATH in finetune.py to point to this dataset.

Run the fine-tuning script:
```
cog run python finetune.py
```
This takes 3.5 hours on a 40GB A100 GPU, and more than that for GPUs with less processing power.

#### Model Communicator
This subsystem is responsible for communication between fine-tuned Student and Tutor models. It also enables communication between base student and Tutor model. The bin folder contains binaries extracted from [llama.cpp](https://github.com/ggerganov/llama.cpp), which helped quantize the tuned Alpaca models. In order to run the script add the base, student and tutor models in models directory.

To run the script, use this command:

```
python3 model_communicator.py B1 base
```

The first argument is the **grade** and the second argument is the **type of model** to use, i.e, base or fine-tuned model for communication. 

PS: If a conversation for a particular context is already generated then it cannot be generated again. It will need to be deleted from the results folder in order to trigger regeneration.


