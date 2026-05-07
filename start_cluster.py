import argparse
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='Launch tracker and peer nodes for the chat cluster.')
    parser.add_argument('--tracker-port', type=int, default=8000, help='Port for the tracker server')
    parser.add_argument('--peer-count', type=int, default=2, help='Number of peer nodes to launch')
    parser.add_argument('--peer-base-port', type=int, default=9001, help='Starting port for peer nodes')
    parser.add_argument('--host', default='127.0.0.1', help='Host/IP to bind servers')
    parser.add_argument('--async-mode', choices=['threading', 'callback', 'coroutine'], default='threading',
                        help='Backend communication mode for tracker and peers')
    parser.add_argument('--python', default=sys.executable, help='Python executable to run the servers')
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path(__file__).resolve().parent
    sampleapp = root / 'start_sampleapp.py'

    if not sampleapp.exists():
        print('ERROR: start_sampleapp.py not found in workspace root.')
        return

    processes = []

    try:
        tracker_cmd = [
            args.python, str(sampleapp),
            '--server-ip', args.host,
            '--server-port', str(args.tracker_port),
            '--role', 'tracker',
            '--tracker-ip', args.host,
            '--tracker-port', str(args.tracker_port),
            '--async-mode', args.async_mode,
        ]
        print('Starting tracker:', ' '.join(tracker_cmd))
        tracker_proc = subprocess.Popen(tracker_cmd)
        processes.append(('tracker', tracker_proc))

        for i in range(args.peer_count):
            port = args.peer_base_port + i
            peer_cmd = [
                args.python, str(sampleapp),
                '--server-ip', args.host,
                '--server-port', str(port),
                '--role', 'peer',
                '--tracker-ip', args.host,
                '--tracker-port', str(args.tracker_port),
                '--async-mode', args.async_mode,
            ]
            print('Starting peer:', ' '.join(peer_cmd))
            peer_proc = subprocess.Popen(peer_cmd)
            processes.append((f'peer-{port}', peer_proc))

        print('\nCluster started:')
        print(f'  tracker -> http://{args.host}:{args.tracker_port}/chat.html')
        for _, proc in processes[1:]:
            print(f'  peer -> port {proc.args[-1]}')
        print('\nPress Ctrl+C to stop all processes.')

        while True:
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f'Process {name} exited with code {proc.returncode}')
                    raise KeyboardInterrupt
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                continue
    except KeyboardInterrupt:
        print('\nStopping cluster...')
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                print(f'Terminating {name} (pid={proc.pid})')
                proc.terminate()
        for name, proc in processes:
            if proc.poll() is None:
                proc.wait(timeout=5)
        print('All processes stopped.')


if __name__ == '__main__':
    main()
