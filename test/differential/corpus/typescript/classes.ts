abstract class Shape {
  constructor(readonly color: string) {}
  abstract area(): number;
}

class Circle extends Shape {
  constructor(color: string, private radius: number) {
    super(color);
  }

  area(): number {
    return Math.PI * this.radius ** 2;
  }
}
