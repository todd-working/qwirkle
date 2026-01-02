# Build stage
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod ./

# Download dependencies (cached if go.mod unchanged)
RUN go mod download

# Copy source
COPY . .

# Build static binary
RUN CGO_ENABLED=0 GOOS=linux go build -o qwirkle ./cmd

# Runtime stage - minimal image
FROM alpine:3.19

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/qwirkle .

# Create static directory for frontend files
RUN mkdir -p static

EXPOSE 8080

ENTRYPOINT ["./qwirkle"]
CMD ["serve", "-addr", ":8080"]
