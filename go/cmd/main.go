// Qwirkle game server and simulator.
package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/todd-working/qwirkle/api"
	"github.com/todd-working/qwirkle/simulator"
)

func main() {
	// Commands
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	switch os.Args[1] {
	case "serve":
		runServer()
	case "simulate":
		runSimulator()
	default:
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println("Qwirkle - Game server and simulator")
	fmt.Println()
	fmt.Println("Usage:")
	fmt.Println("  qwirkle serve      Start the web server")
	fmt.Println("  qwirkle simulate   Run AI vs AI simulations")
	fmt.Println()
	fmt.Println("Run 'qwirkle <command> -h' for command-specific help.")
}

func runServer() {
	fs := flag.NewFlagSet("serve", flag.ExitOnError)
	addr := fs.String("addr", ":8080", "Server address")
	fs.Parse(os.Args[2:])

	server := api.NewServer()
	if err := server.Run(*addr); err != nil {
		fmt.Fprintf(os.Stderr, "Server error: %v\n", err)
		os.Exit(1)
	}
}

func runSimulator() {
	fs := flag.NewFlagSet("simulate", flag.ExitOnError)
	numGames := fs.Int("n", 1000, "Number of games to simulate")
	player1 := fs.String("p1", "greedy", "Player 1 strategy: greedy, random, weighted")
	player2 := fs.String("p2", "greedy", "Player 2 strategy: greedy, random, weighted")
	workers := fs.Int("workers", 0, "Number of parallel workers (0 = num CPUs)")
	seed := fs.Int64("seed", 0, "Random seed (0 = random)")
	output := fs.String("o", "", "Output file (default: stdout)")
	fs.Parse(os.Args[2:])

	config := simulator.Config{
		NumGames: *numGames,
		Player1:  *player1,
		Player2:  *player2,
		Workers:  *workers,
		Seed:     *seed,
	}

	var out *os.File
	var err error
	if *output != "" {
		out, err = os.Create(*output)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Cannot create output file: %v\n", err)
			os.Exit(1)
		}
		defer out.Close()
	} else {
		out = os.Stdout
	}

	runner := simulator.NewRunner(config)
	if err := runner.Run(out); err != nil {
		fmt.Fprintf(os.Stderr, "Simulation error: %v\n", err)
		os.Exit(1)
	}
}
