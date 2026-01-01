# Neuroevolution AI Plan

## Overview

Train a neural network AI using genetic algorithms (neuroevolution) to beat the greedy heuristic solver.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Input Layer (Game State Features)                          │
│  - Score difference (normalized)                            │
│  - Bag remaining (normalized)                               │
│  - Qwirkle potential in hand (0-6 scale)                   │
│  - Board density/spread                                     │
│  - Tiles played this game                                   │
│  - Hand diversity (colors/shapes)                          │
│  Total: ~15-20 features                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Hidden Layer(s)                                            │
│  - 1-2 layers, 16-32 neurons each                          │
│  - ReLU activation                                          │
│  - Small network = fast evaluation                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Output Layer (Strategy Selection)                          │
│  Option A: Softmax over strategies                          │
│    - P(greedy), P(weighted), P(conservative), P(aggressive)│
│  Option B: Direct move scoring adjustment                   │
│    - Multiplier for each move's base score                 │
└─────────────────────────────────────────────────────────────┘
```

## Genetic Algorithm Design

### Genome Representation

Each individual = flattened neural network weights as float array

```go
type Individual struct {
    Weights []float64  // All NN weights flattened
    Fitness float64    // Win rate vs greedy
}
```

### Population Settings

- Population size: 100-200
- Generations: 500-1000
- Elitism: Keep top 10%
- Tournament selection: Size 5

### Mutation Operators

1. **Weight perturbation**: Add Gaussian noise (σ = 0.1)
2. **Weight reset**: Randomly reinitialize 1% of weights
3. **Topology mutation** (optional): Add/remove neurons

### Crossover

- Uniform crossover: 50% chance each weight from parent A or B
- Or: Single-point crossover on weight vector

### Fitness Evaluation

```
For each individual:
    wins = 0
    for i = 1 to 100:
        game = NewGame(seed=i)
        result = play(individual vs greedy)
        if result == WIN: wins++
    fitness = wins / 100
```

## Implementation Phases

### Phase 1: Feature Extraction

Create function to convert GameState → feature vector

```go
func ExtractFeatures(game *GameState) []float64 {
    features := make([]float64, 0, 20)

    // Score difference (normalized to [-1, 1])
    scoreDiff := float64(game.Scores[0] - game.Scores[1]) / 100.0
    features = append(features, scoreDiff)

    // Bag remaining (0-1)
    bagRatio := float64(game.Bag.Remaining()) / 108.0
    features = append(features, bagRatio)

    // Qwirkle potential in hand
    // ... etc

    return features
}
```

### Phase 2: Neural Network (Pure Go)

Simple feedforward network without external dependencies

```go
type NeuralNet struct {
    Layers []Layer
}

type Layer struct {
    Weights [][]float64
    Biases  []float64
}

func (nn *NeuralNet) Forward(input []float64) []float64 {
    current := input
    for _, layer := range nn.Layers {
        current = layer.Forward(current)
    }
    return current
}
```

### Phase 3: Genetic Algorithm

```go
type GA struct {
    Population  []Individual
    PopSize     int
    MutationRate float64
    CrossoverRate float64
}

func (ga *GA) Evolve() {
    // Evaluate fitness (parallelizable)
    ga.EvaluateAll()

    // Selection
    parents := ga.TournamentSelect()

    // Crossover + Mutation
    offspring := ga.CreateOffspring(parents)

    // Replace population (with elitism)
    ga.ReplacePopulation(offspring)
}
```

### Phase 4: Parallel Fitness Evaluation

Use Go's concurrency for fast evaluation

```go
func (ga *GA) EvaluateAll() {
    var wg sync.WaitGroup
    results := make(chan FitnessResult, ga.PopSize)

    for i, ind := range ga.Population {
        wg.Add(1)
        go func(idx int, individual Individual) {
            defer wg.Done()
            fitness := EvaluateFitness(individual, 100) // 100 games
            results <- FitnessResult{idx, fitness}
        }(i, ind)
    }

    // Collect results
    go func() {
        wg.Wait()
        close(results)
    }()

    for result := range results {
        ga.Population[result.Index].Fitness = result.Fitness
    }
}
```

### Phase 5: Training Loop

```go
func Train(generations int) *Individual {
    ga := NewGA(popSize: 100)
    ga.InitializeRandom()

    for gen := 0; gen < generations; gen++ {
        ga.Evolve()

        best := ga.GetBest()
        fmt.Printf("Gen %d: Best fitness = %.2f%%\n", gen, best.Fitness*100)

        // Early stopping if we beat greedy consistently
        if best.Fitness > 0.55 {
            fmt.Println("Found winner!")
            return &best
        }
    }

    return ga.GetBest()
}
```

## Strategy Options for Output

### Option A: Strategy Selector

NN outputs probabilities, sample strategy each turn:

- Greedy (maximize immediate score)
- Weighted (probabilistic scoring)
- Conservative (hold high-value tiles)
- Aggressive (prioritize Qwirkle setups)

### Option B: Move Score Modifier

NN outputs adjustment factors applied to base move scores:

```go
baseScore := move.Score
nnOutput := nn.Forward(features)

// Adjust for tile conservation (don't use Qwirkle-potential tiles early)
adjustedScore := baseScore * nnOutput[0]

// Adjust for board position value
adjustedScore += nnOutput[1] * positionValue(move)
```

## Expected Results

| Generation | Best Fitness | Notes |
|------------|-------------|-------|
| 0 | ~50% | Random weights |
| 100 | ~50-52% | Finding patterns |
| 300 | ~52-55% | Meaningful strategies |
| 500+ | ~55-60%? | Diminishing returns |

**Realistic goal:** 55% win rate vs greedy would be significant.

## Files to Create

```
go/
├── ai/
│   ├── neuroevolution/
│   │   ├── features.go      # Feature extraction
│   │   ├── network.go       # Neural network
│   │   ├── genetic.go       # GA implementation
│   │   └── trainer.go       # Training loop
│   └── neural_solver.go     # Solver using trained NN
│
└── cmd/
    └── train/
        └── main.go          # CLI for training
```

## CLI Usage (Future)

```bash
# Train new model
./qwirkle train -generations 500 -pop 100 -o model.json

# Evaluate model
./qwirkle evaluate -model model.json -games 1000

# Play with trained AI
./qwirkle serve -ai neural -model model.json
```

## Alternative: Hybrid Approach

1. GA evolves simple rule-based switchers first
2. Extract best rules as training data
3. Train NN to interpolate/generalize rules
4. Fine-tune with self-play

This might converge faster than pure neuroevolution.
